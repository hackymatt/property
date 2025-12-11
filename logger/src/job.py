"""Job logger service - consumes job queue and writes JobLog rows (async)"""

from dataclasses import asdict
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


class JobLoggerService:
    def __init__(self, db, rabbitmq):
        self.db = db
        self.rabbitmq = rabbitmq

    async def run(self):
        await self.db.init(retries=STARTUP_RETRIES, delay=STARTUP_RETRY_DELAY)
        # Reflect models from database schema
        await self.db.reflect_models(models.Base)
        models.JobLog = models.Base.classes.joblog

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
        return JobPayload(
            job_id=payload.get("job_id"),
            source=payload.get("source"),
            stage=payload.get("stage"),
            url=payload.get("url"),
            domain=payload.get("domain"),
        )

    async def _handle_message(self, payload: dict, routing_key: str):
        # Extract schedule_run_id, job_run_id and status from routing key: job.{schedule_run_id}.{job_run_id}.{status}
        parts = routing_key.split(".")
        schedule_run_id = parts[1] if len(parts) > 1 else None
        job_run_id = parts[2] if len(parts) > 2 else None
        status = parts[3] if len(parts) > 3 else None

        job_payload = self._parse_payload(payload)
        job_id = job_payload.job_id
        metadata = {
            "source": job_payload.source,
            "stage": job_payload.stage,
            "url": job_payload.url,
            "domain": job_payload.domain,
        }

        async with self.db.get_session() as session:
            now = datetime.now(timezone.utc)
            log_entry = models.JobLog(
                schedule_run_id=schedule_run_id,
                job_run_id=job_run_id,
                job_id=job_id,
                status=status,
                metadata=metadata,
                created_at=now,
                updated_at=now,
            )
            session.add(log_entry)
            await session.commit()
        logger.info(
            f"Inserted JobLog for schedule_run_id={schedule_run_id} job_run_id={job_run_id} job_id={job_id} status={status} source={job_payload.source}"
        )
