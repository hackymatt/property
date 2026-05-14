"""Scraper service - consumes job queue and executes scrapers"""

import uuid

from config import (
    RABBITMQ_JOB_QUEUE,
    RABBITMQ_JOB_EXCHANGE,
    RABBITMQ_DATA_EXCHANGE,
    RABBITMQ_EXCHANGE_TYPE,
    RABBITMQ_ROUTING_KEY,
    RABBITMQ_THROTTLE_QUEUE,
    STARTUP_RETRIES,
    STARTUP_RETRY_DELAY,
)
from shared.payloads import JobPayload, DataPayload
from shared.consts import Status, Stage
from shared.throttle_helper import ThrottleHelper
from src.sdk.request import RetriableError, TooManyRequestsError
from src.source_loader import SourceLoader
from src.deduplicator import JobDeduplicator
from src.scrape import scrape
from src.logger import logger


class ScraperService:
    def __init__(self, rabbitmq, db, deduplicator: JobDeduplicator):
        self.rabbitmq = rabbitmq
        self.db = db
        self.deduplicator = deduplicator
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

        # Deduplicate at consume time — drop if already processed recently
        if not await self.deduplicator.mark_processed(params.source, params.stage, params.url):
            logger.info(
                "[SCRAPER] Duplicate job skipped source=%s stage=%s url=%s",
                params.source, params.stage, params.url,
            )
            return

        logger.info(
            "[SCRAPER] Received %s job schedule_run_id=%s job_run_id=%s: %s",
            status, schedule_run_id, job_run_id, payload,
        )

        try:
            await self._publish_status(schedule_run_id, job_run_id, Status.RUNNING, job_payload)

            result = await scrape(params, throttle_helper=self.throttle_helper, source_loader=self.source_loader)

            logger.info("[SCRAPER] Job result job_run_id=%s: %s", job_run_id, result)

            await self._create_followup_jobs(
                schedule_run_id=schedule_run_id,
                parent_job_run_id=job_run_id,
                job_payload=job_payload,
                stage=params.stage,
                result=result,
            )

            logger.info("[SCRAPER] Job completed successfully job_run_id=%s", job_run_id)
            await self._publish_status(
                schedule_run_id, job_run_id, Status.SUCCESS,
                job_payload.model_copy(update={"metadata": {"result": result if isinstance(result, list) else None}}),
            )

        except RetriableError as exc:
            logger.warning(
                "[SCRAPER] Retriable error on job_run_id=%s (%s), requeueing after %ss pause",
                job_run_id, exc, exc.retry_after,
            )
            await self.deduplicator.clear(params.source, params.stage, params.url)
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

    async def _create_followup_jobs(self, schedule_run_id, parent_job_run_id, job_payload, stage, result):
        stage_mapping = {
            Stage.LIST_PAGES: Stage.LIST_ITEMS,
            Stage.LIST_ITEMS: Stage.GET_ITEM,
            Stage.GET_ITEM: None,
        }

        next_stage = stage_mapping.get(stage)
        if not next_stage:
            routing_key = f"data.{schedule_run_id}.{parent_job_run_id}.pending"
            await self.rabbitmq.publish_to_exchange(
                exchange=RABBITMQ_DATA_EXCHANGE,
                routing_key=routing_key,
                message=result.model_dump(),
                exchange_type=RABBITMQ_EXCHANGE_TYPE,
            )
            logger.info("[SCRAPER] Forwarded DataPayload for job_run_id=%s", parent_job_run_id)
            return

        urls = result
        if not urls:
            logger.info("[SCRAPER] No URLs in result — no follow-up jobs created")
            return

        jobs_created = 0
        skipped = 0
        for url in urls:
            if not isinstance(url, str):
                logger.warning("[SCRAPER] Skipping non-string URL: %s", url)
                continue

            if not await self.deduplicator.mark_queued(job_payload.source, next_stage, url):
                skipped += 1
                continue

            job_run_id = str(uuid.uuid4())
            follow_up = job_payload.model_copy(
                update={"parent_job_run_id": parent_job_run_id, "stage": next_stage, "url": url}
            )
            await self.rabbitmq.publish_to_exchange(
                exchange=RABBITMQ_JOB_EXCHANGE,
                routing_key=f"job.{schedule_run_id}.{job_run_id}.pending",
                message=follow_up.model_dump(),
                exchange_type=RABBITMQ_EXCHANGE_TYPE,
            )
            jobs_created += 1

        logger.info(
            "[SCRAPER] Created %d follow-up jobs (%d duplicates skipped): %s → %s",
            jobs_created, skipped, stage, next_stage,
        )
