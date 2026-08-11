"""Job logger service - consumes job queue and writes JobRunLog rows (async)"""

from datetime import datetime, timezone

from src.logger import logger
from config import (
    RABBITMQ_JOB_QUEUE,
    RABBITMQ_JOB_EXCHANGE,
    RABBITMQ_EXCHANGE_TYPE,
    RABBITMQ_JOB_ROUTING_KEY,
    STARTUP_RETRIES,
    STARTUP_RETRY_DELAY,
)
from src import models
from shared.payloads import JobPayload


class JobRunLoggerService:
    def __init__(self, db, rabbitmq):
        self.db = db
        self.rabbitmq = rabbitmq

    async def run(self):
        await self.db.init(retries=STARTUP_RETRIES, delay=STARTUP_RETRY_DELAY)
        # Reflect models from database schema
        await self.db.reflect_models(models.Base)
        models.JobRunLog = models.Base.classes.jobrunlog

        await self.rabbitmq.connect_with_retry(
            retries=STARTUP_RETRIES,
            delay=STARTUP_RETRY_DELAY,
            logger=logger,
        )
        await self.rabbitmq.bind_queue_to_exchange(
            queue=RABBITMQ_JOB_QUEUE,
            exchange=RABBITMQ_JOB_EXCHANGE,
            routing_key=RABBITMQ_JOB_ROUTING_KEY,
            exchange_type=RABBITMQ_EXCHANGE_TYPE,
        )
        logger.info(
            "Job logger started; waiting for messages on queue '%s' bound to exchange '%s' with routing_key '%s'",
            RABBITMQ_JOB_QUEUE,
            RABBITMQ_JOB_EXCHANGE,
            RABBITMQ_JOB_ROUTING_KEY,
        )
        await self.rabbitmq.consume_forever(
            queue=RABBITMQ_JOB_QUEUE,
            handler=self._handle_message,
            durable=True,
        )

    def _parse_payload(self, payload: dict) -> JobPayload:
        return JobPayload.model_validate(payload)

    @staticmethod
    def _summarize_metadata(metadata):
        """`result` is transient plumbing between scraper and bench — for a
        final stage it holds the whole batch of records, which already lands
        in PropertyRaw. Persisting it here would duplicate megabytes per run
        log row, so keep only its size. Everything else (error_message,
        file_id, fingerprint, ...) is retained verbatim — bench's
        change-detection reads fingerprint back out of these rows."""
        if not isinstance(metadata, dict):
            return metadata

        summarized = dict(metadata)
        # Bulky, transient plumbing: keep the size, drop the payload.
        for key in ("result", "image_urls"):
            if key in summarized:
                value = summarized.pop(key)
                summarized[f"{key}_count"] = len(value) if isinstance(value, list) else None
        return summarized

    async def _handle_message(self, payload: dict, routing_key: str):
        # Extract schedule_run_id, job_run_id and status from routing key: job.{schedule_run_id}.{job_run_id}.{status}
        parts = routing_key.split(".")
        schedule_run_id = parts[1] if len(parts) > 1 else None
        job_run_id = parts[2] if len(parts) > 2 else None
        status = parts[3] if len(parts) > 3 else None

        job_payload = self._parse_payload(payload)
        parent_job_run_id = job_payload.parent_job_run_id or None
        metadata = self._summarize_metadata(payload.get("metadata", {}))

        async with self.db.get_session() as session:
            now = datetime.now(timezone.utc)
            log_entry = models.JobRunLog(
                schedule_run_id=schedule_run_id,
                parent_job_run_id=parent_job_run_id,
                job_run_id=job_run_id,
                domain_name=job_payload.domain_name,
                source=job_payload.source,
                stage=job_payload.stage,
                url=job_payload.url,
                status=status,
                metadata=metadata,
                created_at=now,
                updated_at=now,
            )
            session.add(log_entry)
            await session.commit()
        logger.info(
            f"Inserted JobRunLog for schedule_run_id={schedule_run_id} job_run_id={job_run_id} status={status} source={job_payload.source}"
        )
