"""Scraper service - consumes job queue, executes exactly one stage per job.

Does NOT decide what runs next (that's bench's job, based on
ScraperSourceStage order) — publishes a status event with the stage's raw
result attached and stops. This split (execute one stage / decide next
stage) is what lets the same engine serve both PORTAL_LISTING (Otodom) and
FILE_REGISTRY (RCN) sources without the engine knowing anything about
either domain."""

import uuid

from config import (
    RABBITMQ_JOB_QUEUE,
    RABBITMQ_JOB_EXCHANGE,
    RABBITMQ_EXCHANGE_TYPE,
    RABBITMQ_ROUTING_KEY,
    RABBITMQ_THROTTLE_QUEUE,
    STARTUP_RETRIES,
    STARTUP_RETRY_DELAY,
)
from shared.payloads import JobPayload
from shared.consts import Status
from shared.throttle_helper import ThrottleHelper
from src.sdk.request import RetriableError
from src.source_loader import SourceLoader
from src.scrape import scrape
from src.logger import logger


class ScraperService:
    def __init__(self, rabbitmq, db):
        self.rabbitmq = rabbitmq
        self.db = db
        self.throttle_helper = None
        self.source_loader = None

    async def run(self):
        await self.db.init(retries=STARTUP_RETRIES, delay=STARTUP_RETRY_DELAY)
        self.source_loader = SourceLoader(self.db)
        await self.source_loader.init()
        logger.info("SourceLoader initialized")

        await self.rabbitmq.connect_with_retry(
            retries=STARTUP_RETRIES, delay=STARTUP_RETRY_DELAY, logger=logger,
        )

        self.throttle_helper = ThrottleHelper(
            rabbitmq_client=self.rabbitmq, throttle_queue=RABBITMQ_THROTTLE_QUEUE,
        )
        await self.throttle_helper.start()
        logger.info("ThrottleHelper initialized")

        await self.rabbitmq.bind_queue_to_exchange(
            queue=RABBITMQ_JOB_QUEUE,
            exchange=RABBITMQ_JOB_EXCHANGE,
            routing_key=RABBITMQ_ROUTING_KEY,
            exchange_type=RABBITMQ_EXCHANGE_TYPE,
        )
        logger.info(
            "Scraper bound to exchange '%s' routing_key '%s' queue '%s'",
            RABBITMQ_JOB_EXCHANGE, RABBITMQ_ROUTING_KEY, RABBITMQ_JOB_QUEUE,
        )
        await self.rabbitmq.consume_forever(
            queue=RABBITMQ_JOB_QUEUE, handler=self._handle_message, durable=True,
        )

    async def _handle_message(self, payload: dict, routing_key: str):
        parts = routing_key.split(".")
        schedule_run_id = parts[1] if len(parts) > 1 else None
        job_run_id = parts[2] if len(parts) > 2 else None
        status = parts[3] if len(parts) > 3 else None

        job_payload = self._parse_payload(payload)
        params = JobPayload(**payload)

        logger.info(
            "[SCRAPER] Received %s job schedule_run_id=%s job_run_id=%s: %s",
            status, schedule_run_id, job_run_id, payload,
        )

        try:
            await self._publish_status(schedule_run_id, job_run_id, Status.RUNNING, job_payload)

            result = await scrape(
                params,
                throttle_helper=self.throttle_helper,
                source_loader=self.source_loader,
                rabbitmq=self.rabbitmq,
                schedule_run_id=schedule_run_id,
                job_run_id=job_run_id,
            )

            logger.info("[SCRAPER] Job result job_run_id=%s: %s", job_run_id, result)

            await self._publish_status(
                schedule_run_id, job_run_id, Status.SUCCESS,
                job_payload.model_copy(
                    update={"metadata": {**(job_payload.metadata or {}), "result": result}}
                ),
            )

            logger.info("[SCRAPER] Job completed successfully job_run_id=%s", job_run_id)

        except RetriableError as exc:
            logger.warning(
                "[SCRAPER] Retriable error on job_run_id=%s (%s), requeueing after %ss pause",
                job_run_id, exc, exc.retry_after,
            )
            await self.rabbitmq.publish_to_exchange(
                exchange=RABBITMQ_JOB_EXCHANGE,
                routing_key=f"job.{schedule_run_id}.{uuid.uuid4()}.pending",
                message=job_payload.model_dump(),
                exchange_type=RABBITMQ_EXCHANGE_TYPE,
            )

        except Exception as exc:
            logger.error("[SCRAPER] Job exception job_run_id=%s: %s", job_run_id, exc, exc_info=True)
            await self._publish_status(
                schedule_run_id, job_run_id, Status.FAILED,
                job_payload.model_copy(update={"metadata": {"error_message": str(exc), "error_trace": repr(exc)}}),
            )

    def _parse_payload(self, payload: dict) -> JobPayload:
        return JobPayload.model_validate(payload)

    async def _publish_status(self, schedule_run_id, job_run_id, status, job_payload):
        routing_key = f"job.{schedule_run_id}.{job_run_id}.{status}"
        await self.rabbitmq.publish_to_exchange(
            exchange=RABBITMQ_JOB_EXCHANGE,
            routing_key=routing_key,
            message=job_payload.model_dump(),
            exchange_type=RABBITMQ_EXCHANGE_TYPE,
        )
        logger.info(
            "[SCRAPER] Published %s status for schedule_run_id=%s job_run_id=%s",
            status, schedule_run_id, job_run_id,
        )
