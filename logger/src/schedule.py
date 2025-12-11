"""Schedule logger service - consumes schedule queue and writes ScheduleLog rows (async)"""

from dataclasses import asdict
from datetime import datetime, timezone

from src.logger import logger
from config import (
    RABBITMQ_SCHEDULE_QUEUE,
    RABBITMQ_SCHEDULE_EXCHANGE,
    RABBITMQ_EXCHANGE_TYPE,
    RABBITMQ_ROUTING_KEY,
    STARTUP_RETRIES,
    STARTUP_RETRY_DELAY,
)
from src import models
from shared.payloads import SchedulePayload, JobPayload


class ScheduleLoggerService:
    def __init__(self, db, rabbitmq):
        self.db = db
        self.rabbitmq = rabbitmq

    async def run(self):
        await self.db.init(retries=STARTUP_RETRIES, delay=STARTUP_RETRY_DELAY)
        # Reflect models from database schema
        await self.db.reflect_models(models.Base)
        models.ScheduleLog = models.Base.classes.schedulelog

        await self.rabbitmq.connect_with_retry(
            retries=STARTUP_RETRIES,
            delay=STARTUP_RETRY_DELAY,
            logger=logger,
        )
        await self.rabbitmq.bind_queue_to_exchange(
            queue=RABBITMQ_SCHEDULE_QUEUE,
            exchange=RABBITMQ_SCHEDULE_EXCHANGE,
            routing_key=RABBITMQ_ROUTING_KEY,
            exchange_type=RABBITMQ_EXCHANGE_TYPE,
        )
        logger.info(
            "Logger started; waiting for messages on queue '%s' bound to exchange '%s' with routing_key '%s'",
            RABBITMQ_SCHEDULE_QUEUE,
            RABBITMQ_SCHEDULE_EXCHANGE,
            RABBITMQ_ROUTING_KEY,
        )
        await self.rabbitmq.consume_forever(
            queue=RABBITMQ_SCHEDULE_QUEUE,
            handler=self._handle_message,
            durable=True,
        )

    def _parse_payload(self, payload: dict) -> SchedulePayload:
        jobs_raw = payload.get("jobs", [])
        jobs = [
            job if isinstance(job, JobPayload) else JobPayload(**job)
            for job in jobs_raw
        ]

        return SchedulePayload(
            schedule_id=payload.get("schedule_id"),
            jobs=jobs,
        )

    async def _handle_message(self, payload: dict, routing_key: str):
        # Extract schedule_run_id and status from routing key: schedule.{schedule_run_id}.{status}
        parts = routing_key.split(".")
        schedule_run_id = parts[1] if len(parts) > 1 else None
        status = parts[2] if len(parts) > 2 else None

        schedule_payload = self._parse_payload(payload)
        schedule_id = schedule_payload.schedule_id
        metadata = {"jobs": [asdict(job) for job in schedule_payload.jobs]}

        async with self.db.get_session() as session:
            now = datetime.now(timezone.utc)
            log_entry = models.ScheduleLog(
                schedule_run_id=schedule_run_id,
                schedule_id=schedule_id,
                status=status,
                metadata=metadata,
                created_at=now,
                updated_at=now,
            )
            session.add(log_entry)
            await session.commit()
        logger.info(
            f"Inserted ScheduleLog for schedule_run_id={schedule_run_id} schedule_id={schedule_id} status={status}"
        )
