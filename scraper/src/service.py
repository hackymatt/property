"""Scraper service - consumes job queue and executes scrapers"""

import uuid
from dataclasses import asdict

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
from shared.consts import Status, Stage
from shared.throttle_helper import ThrottleHelper
from src.scrape import scrape
from src.logger import logger


class ScraperService:
    def __init__(self, rabbitmq):
        self.rabbitmq = rabbitmq
        self.throttle_helper = None

    async def run(self):
        await self.rabbitmq.connect_with_retry(
            retries=STARTUP_RETRIES,
            delay=STARTUP_RETRY_DELAY,
            logger=logger,
        )

        # Initialize throttle helper
        self.throttle_helper = ThrottleHelper(
            rabbitmq_client=self.rabbitmq,
            throttle_queue=RABBITMQ_THROTTLE_QUEUE,
        )
        await self.throttle_helper.start()
        logger.info("Throttle helper initialized")

        await self.rabbitmq.bind_queue_to_exchange(
            queue=RABBITMQ_JOB_QUEUE,
            exchange=RABBITMQ_JOB_EXCHANGE,
            routing_key=RABBITMQ_ROUTING_KEY,
            exchange_type=RABBITMQ_EXCHANGE_TYPE,
        )
        logger.info(
            "Scraper service initialized; bound to exchange '%s' with routing_key '%s'",
            RABBITMQ_JOB_EXCHANGE,
            RABBITMQ_ROUTING_KEY,
        )
        logger.info(
            "Scraper service ready to consume jobs from queue '%s'", RABBITMQ_JOB_QUEUE
        )
        await self.rabbitmq.consume_forever(
            queue=RABBITMQ_JOB_QUEUE,
            handler=self._handle_message,
            durable=True,
        )

    async def _handle_message(self, payload: dict, routing_key: str):
        """Handle incoming job message"""
        # Extract schedule_run_id, job_run_id and status from routing key: job.{schedule_run_id}.{job_run_id}.{status}
        parts = routing_key.split(".")
        schedule_run_id = parts[1] if len(parts) > 1 else None
        job_run_id = parts[2] if len(parts) > 2 else None
        status = parts[3] if len(parts) > 3 else None

        logger.info(
            "[SCRAPER] Received %s job schedule_run_id=%s job_run_id=%s: %s",
            status,
            schedule_run_id,
            job_run_id,
            payload,
        )

        job_payload = self._parse_payload(payload)

        try:
            # Execute scraper with throttle_helper for per-request throttling
            params = JobPayload(**payload)

            await self._publish_status(
                schedule_run_id, job_run_id, Status.RUNNING, job_payload
            )

            # Pass throttle_helper to scrape - per-request throttling happens in Browser.goto()
            result = await scrape(params, throttle_helper=self.throttle_helper)

            logger.info("[SCRAPER] Job result job_run_id=%s: %s", job_run_id, result)

            # Create follow-up jobs based on stage and results
            await self._create_followup_jobs(
                schedule_run_id=schedule_run_id,
                parent_job_run_id=job_run_id,
                job_payload=job_payload,
                stage=params.stage,
                result=result,
            )

            logger.info(
                "[SCRAPER] Job completed successfully job_run_id=%s", job_run_id
            )
            success_payload_dict = asdict(job_payload)
            success_payload_dict["metadata"] = {"result": result}
            success_payload = JobPayload(**success_payload_dict)

            await self._publish_status(
                schedule_run_id, job_run_id, Status.SUCCESS, success_payload
            )

        except Exception as exc:
            logger.error(
                "[SCRAPER] Job exception job_run_id=%s: %s",
                job_run_id,
                exc,
                exc_info=True,
            )
            failed_payload_dict = asdict(job_payload)
            failed_payload_dict["metadata"] = {
                "error_message": str(exc),
                "error_trace": repr(exc),
            }
            failed_payload = JobPayload(**failed_payload_dict)
            await self._publish_status(
                schedule_run_id, job_run_id, Status.FAILED, failed_payload
            )

    def _parse_payload(self, payload: dict) -> JobPayload:
        return JobPayload(
            source=payload.get("source"),
            stage=payload.get("stage"),
            url=payload.get("url"),
            domain_name=payload.get("domain_name"),
            parent_job_run_id=payload.get("parent_job_run_id"),
            metadata=payload.get("metadata"),
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

    async def _create_followup_jobs(
        self,
        schedule_run_id: str,
        parent_job_run_id: str,
        job_payload: JobPayload,
        stage: str,
        result: list | dict,
    ):
        """Create follow-up jobs based on the stage and result

        Stage progression:
        - list_pages -> list_items (one job per page URL)
        - list_items -> get_item (one job per item URL)
        - get_item -> no follow-up (final stage)
        """
        stage_mapping = {
            Stage.LIST_PAGES: Stage.LIST_ITEMS,
            # Stage.LIST_ITEMS: Stage.GET_ITEM,
        }

        next_stage = stage_mapping.get(stage)
        if not next_stage:
            # publish save data pending event
            logger.info(
                "[SCRAPER] No follow-up stage for '%s', job chain complete", stage
            )
            return

        urls = result
        if not urls:
            logger.info("[SCRAPER] No URLs found in result, no follow-up jobs created")
            return

        # Create a job for each URL
        jobs_created = 0
        for url in urls:
            if not isinstance(url, str):
                logger.warning("[SCRAPER] Skipping non-string URL: %s", url)
                continue

            job_run_id = str(uuid.uuid4())
            payload_dict = asdict(job_payload)
            payload_dict.update(
                {
                    "parent_job_run_id": parent_job_run_id,
                    "stage": next_stage,
                    "url": url,
                }
            )
            follow_up_payload = JobPayload(**payload_dict)

            job_routing_key = f"job.{schedule_run_id}.{job_run_id}.pending"
            await self.rabbitmq.publish_to_exchange(
                exchange=RABBITMQ_JOB_EXCHANGE,
                routing_key=job_routing_key,
                message=asdict(follow_up_payload),
                exchange_type=RABBITMQ_EXCHANGE_TYPE,
            )
            jobs_created += 1

        logger.info(
            "[SCRAPER] Created %d follow-up jobs: %s -> %s",
            jobs_created,
            stage,
            next_stage,
        )
