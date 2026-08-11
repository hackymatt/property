"""Data ingestion service - consumes data_exchange, writes insert-only to PropertyRaw.

The only writer of PropertyRaw. Idempotent by construction: content_hash is
computed here and the insert is `ON CONFLICT (source_id, external_ref,
content_hash) DO NOTHING`, so redelivery or reprocessing never creates
duplicate rows — a new row only appears when the observed content actually
changed."""

import hashlib
import json as json_lib
from datetime import datetime, timezone

from sqlalchemy import select

from config import (
    RABBITMQ_DATA_QUEUE,
    RABBITMQ_DATA_EXCHANGE,
    RABBITMQ_EXCHANGE_TYPE,
    RABBITMQ_DATA_ROUTING_KEY,
    STARTUP_RETRIES,
    STARTUP_RETRY_DELAY,
)
from shared.payloads import DataExchangePayload
from src.db_utils import insert_ignore
from src.logger import logger
from src import models


def _content_hash(data: dict, ignore_keys: list | None = None) -> str:
    """Hash of the payload, optionally ignoring noisy top-level keys.

    content_hash decides what counts as a CHANGE, so it must cover only
    fields that describe the thing itself. Otodom, for example, embeds
    `userAdverts` — the seller's *other* listings — which churns on its own
    and would otherwise mark a listing as changed on almost every crawl.

    The record is still stored verbatim; only the change-detection
    projection skips these keys. Configured per source via
    ScraperSource.config["hash_ignore"].
    """
    if ignore_keys:
        data = {key: value for key, value in data.items() if key not in set(ignore_keys)}
    canonical = json_lib.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class Service:
    def __init__(self, db, rabbitmq):
        self.db = db
        self.rabbitmq = rabbitmq

    async def run(self):
        await self.db.init(retries=STARTUP_RETRIES, delay=STARTUP_RETRY_DELAY)
        await self.db.reflect_models(models.Base)
        models.PropertyRaw = models.Base.classes.property_raw
        models.ScraperSource = models.Base.classes.scraper_source
        logger.info("Database initialized and models reflected")

        await self.rabbitmq.connect_with_retry(
            retries=STARTUP_RETRIES,
            delay=STARTUP_RETRY_DELAY,
            logger=logger,
        )
        await self.rabbitmq.bind_queue_to_exchange(
            queue=RABBITMQ_DATA_QUEUE,
            exchange=RABBITMQ_DATA_EXCHANGE,
            routing_key=RABBITMQ_DATA_ROUTING_KEY,
            exchange_type=RABBITMQ_EXCHANGE_TYPE,
        )
        logger.info(
            "Data ingestion started; waiting for messages on queue '%s' bound to exchange '%s' routing_key '%s'",
            RABBITMQ_DATA_QUEUE,
            RABBITMQ_DATA_EXCHANGE,
            RABBITMQ_DATA_ROUTING_KEY,
        )
        await self.rabbitmq.consume_forever(
            queue=RABBITMQ_DATA_QUEUE,
            handler=self._handle_message,
            durable=True,
        )

    def _parse_payload(self, payload: dict) -> DataExchangePayload:
        return DataExchangePayload.model_validate(payload)

    async def _handle_message(self, payload: dict, routing_key: str):
        record = self._parse_payload(payload)
        logger.info(
            "[DATA_INGESTION] Received record source=%s external_ref=%s",
            record.source,
            record.external_ref,
        )

        async with self.db.get_session() as session:
            async with session.begin():
                source = (
                    await session.execute(
                        select(models.ScraperSource).where(models.ScraperSource.name == record.source)
                    )
                ).scalar_one_or_none()

                if source is None:
                    logger.error(
                        "[DATA_INGESTION] Unknown source '%s' — skipping external_ref=%s",
                        record.source,
                        record.external_ref,
                    )
                    return

                now = datetime.now(timezone.utc)
                values = {
                    "property_type": record.property_type or source.property_type,
                    "source_id": source.id,
                    "external_ref": record.external_ref,
                    "content_hash": _content_hash(
                        record.data, (source.config or {}).get("hash_ignore")
                    ),
                    "json": record.data,
                    "job_run_id": record.job_run_id,
                    "partition_date": now.date(),
                    "created_at": now,
                }

                await insert_ignore(
                    session,
                    models.PropertyRaw,
                    values,
                    index_elements=["source_id", "external_ref", "content_hash"],
                )

        logger.info(
            "[DATA_INGESTION] Completed source=%s external_ref=%s (no-op if content unchanged)",
            record.source,
            record.external_ref,
        )
