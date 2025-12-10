"""Schedule logger service - consumes schedule queue and writes ScheduleLog rows (async)"""

from datetime import datetime, timezone

from shared.database import DatabaseManager
from src.logger import logger
from config import (
    RABBITMQ_SCHEDULE_QUEUE,
    STARTUP_RETRIES,
    STARTUP_RETRY_DELAY,
    DATABASE_URL,
)
from src import models


class ScheduleLoggerService:
    def __init__(self, rabbitmq):
        self.db = DatabaseManager(
            database_url=DATABASE_URL, logger_name="schedule-logger"
        )
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
        logger.info("Schedule logger started; waiting for messages...")
        await self.rabbitmq.consume_forever(
            queue=RABBITMQ_SCHEDULE_QUEUE,
            handler=self._handle_message,
            durable=True,
        )

    async def _handle_message(self, payload: dict):
        run_id = payload.pop("run_id")
        schedule_id = payload.pop("schedule_id")
        status = payload.pop("status")
        metadata = payload  # remaining fields as metadata

        async with self.db.get_session() as session:
            now = datetime.now(timezone.utc)
            log_entry = models.ScheduleLog(
                run_id=run_id,
                schedule_id=schedule_id,
                status=status,
                metadata=metadata,
                created_at=now,
                updated_at=now,
            )
            session.add(log_entry)
            await session.commit()
        logger.info(
            f"Inserted ScheduleLog for run_id={run_id} schedule_id={schedule_id} status={status}"
        )
