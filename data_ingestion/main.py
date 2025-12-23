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
from src.service import Service


async def main():
    try:
        db = DatabaseManager(database_url=DATABASE_URL, logger_name="data_ingestion")

        rabbitmq = RabbitMQClient(
            host=RABBITMQ_HOST,
            port=RABBITMQ_PORT,
            username=RABBITMQ_USER,
            password=RABBITMQ_PASSWORD,
            virtual_host=RABBITMQ_VHOST,
        )

        service = Service(db=db, rabbitmq=rabbitmq)

        await service.run()
    except KeyboardInterrupt:
        logger.warning("Data ingestion interrupted by user")
    except Exception as exc:
        logger.critical(f"Data ingestion terminated: {exc}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
