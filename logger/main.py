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
        service = ScheduleLoggerService(db=db, rabbitmq=rabbitmq)
        await service.run()
    except KeyboardInterrupt:
        logger.warning("Logger interrupted by user")
    except Exception as exc:
        logger.critical(f"Logger terminated: {exc}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
