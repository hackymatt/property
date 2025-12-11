"""Scraper service - consumes job queue and executes scrapers"""

from dataclasses import asdict

from config import (
    RABBITMQ_JOB_QUEUE,
    RABBITMQ_JOB_EXCHANGE,
    RABBITMQ_EXCHANGE_TYPE,
    RABBITMQ_ROUTING_KEY,
    STARTUP_RETRIES,
    STARTUP_RETRY_DELAY,
)
from shared.payloads import JobPayload
from shared.consts import Status
from src.scrape import scrape
from src.logger import logger


class ScraperService:
    def __init__(self, rabbitmq):
        self.rabbitmq = rabbitmq

    async def run(self):
        await self.rabbitmq.connect_with_retry(
            retries=STARTUP_RETRIES,
            delay=STARTUP_RETRY_DELAY,
            logger=logger,
        )
        await self.rabbitmq.bind_queue_to_exchange(
            queue=RABBITMQ_JOB_QUEUE,
            exchange=RABBITMQ_JOB_EXCHANGE,
            routing_key=RABBITMQ_ROUTING_KEY,
            exchange_type=RABBITMQ_EXCHANGE_TYPE,
        )
        logger.info(
            "Scraper service started; waiting for jobs on queue '%s' bound to exchange '%s' with routing_key '%s'",
            RABBITMQ_JOB_QUEUE,
            RABBITMQ_JOB_EXCHANGE,
            RABBITMQ_ROUTING_KEY,
        )
        await self.rabbitmq.consume_forever(
            queue=RABBITMQ_JOB_QUEUE,
            handler=self._handle_message,
            durable=True,
        )

    async def _handle_message(self, payload: dict, routing_key: str):
        """Handle incoming job message"""
        # Extract run_id, job_id and status from routing key: job.{run_id}.{job_id}.{status}
        parts = routing_key.split(".")
        schedule_run_id = parts[1] if len(parts) > 1 else None
        run_id = parts[2] if len(parts) > 2 else None
        status = parts[3] if len(parts) > 3 else None

        logger.info(
            "[SCRAPER] Received %s job schedule_run_id=%s run_id=%s: %s",
            status,
            schedule_run_id,
            run_id,
            payload,
        )

        job_payload = self._parse_payload(payload)

        try:
            # Execute scraper
            params = JobPayload(**payload)
            # result = await scrape(params)

            await self._publish_status(
                schedule_run_id, run_id, Status.RUNNING, job_payload
            )

            logger.info("[SCRAPER] Job completed successfully run_id=%s", run_id)
            await self._publish_status(
                schedule_run_id, run_id, Status.SUCCESS, job_payload
            )

        except Exception as exc:
            logger.error(
                "[SCRAPER] Job exception run_id=%s: %s", run_id, exc, exc_info=True
            )
            await self._publish_status(
                schedule_run_id, run_id, Status.FAILED, job_payload
            )

    def _parse_payload(self, payload: dict) -> JobPayload:
        return JobPayload(
            job_id=payload.get("job_id"),
            source=payload.get("source"),
            stage=payload.get("stage"),
            url=payload.get("url"),
            domain=payload.get("domain"),
        )

    async def _publish_status(
        self,
        schedule_run_id: str,
        job_run_id: str,
        status: str,
        job_payload: JobPayload,        
    ):
        """Publish job status update to exchange"""
        routing_key = f"job.{schedule_run_id}.{job_run_id}.{status}"
        message = asdict(job_payload)

        await self.rabbitmq.publish_to_exchange(
            exchange=RABBITMQ_JOB_EXCHANGE,
            routing_key=routing_key,
            message=message,
            exchange_type=RABBITMQ_EXCHANGE_TYPE,
        )
        logger.info(
            "[SCRAPER] Published %s status for schedule_run_id=%s job_run_id=%s",
            status,
            schedule_run_id,
            job_run_id,
        )
