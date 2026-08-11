import asyncio
from config import (
    RABBITMQ_HOST, RABBITMQ_PORT, RABBITMQ_USER, RABBITMQ_PASSWORD, RABBITMQ_VHOST,
    DATABASE_URL,
)
from shared.rabbitmq import RabbitMQClient
from shared.database import DatabaseManager
from src.service import ScraperService


async def main():
    rabbitmq = RabbitMQClient(
        host=RABBITMQ_HOST, port=RABBITMQ_PORT,
        username=RABBITMQ_USER, password=RABBITMQ_PASSWORD,
        virtual_host=RABBITMQ_VHOST,
    )
    db = DatabaseManager(database_url=DATABASE_URL, logger_name="scraper.db")

    service = ScraperService(rabbitmq=rabbitmq, db=db)
    await service.run()


if __name__ == "__main__":
    asyncio.run(main())
