import sys
import asyncio

from src.logger import logger
from config import (
    DATABASE_URL,
    RABBITMQ_HOST,
    RABBITMQ_PORT,
    RABBITMQ_USER,
    RABBITMQ_PASSWORD,
    RABBITMQ_VHOST,
)
from shared.database import DatabaseManager
from shared.rabbitmq import RabbitMQClient
from src.schedule import ScheduleLoggerService
from src.job import JobLoggerService


async def main():
    try:
        db = DatabaseManager(database_url=DATABASE_URL, logger_name="logger")

        rabbitmq = RabbitMQClient(
            host=RABBITMQ_HOST,
            port=RABBITMQ_PORT,
            username=RABBITMQ_USER,
            password=RABBITMQ_PASSWORD,
            virtual_host=RABBITMQ_VHOST,
        )

        # Run both schedule and job logger services concurrently
        schedule_service = ScheduleLoggerService(db=db, rabbitmq=rabbitmq)
        job_service = JobLoggerService(db=db, rabbitmq=rabbitmq)

        await asyncio.gather(
            schedule_service.run(),
            job_service.run(),
        )
    except KeyboardInterrupt:
        logger.warning("Logger interrupted by user")
    except Exception as exc:
        logger.critical(f"Logger terminated: {exc}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
