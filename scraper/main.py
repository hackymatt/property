import asyncio
from config import (
    RABBITMQ_HOST, RABBITMQ_PORT, RABBITMQ_USER, RABBITMQ_PASSWORD, RABBITMQ_VHOST,
    REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_PASSWORD,
    DATABASE_URL, STARTUP_RETRIES, STARTUP_RETRY_DELAY,
)
from shared.rabbitmq import RabbitMQClient
from shared.database import DatabaseManager
from shared.redis_client import RedisClient
from src.deduplicator import JobDeduplicator
from src.service import ScraperService


async def main():
    rabbitmq = RabbitMQClient(
        host=RABBITMQ_HOST, port=RABBITMQ_PORT,
        username=RABBITMQ_USER, password=RABBITMQ_PASSWORD,
        virtual_host=RABBITMQ_VHOST,
    )
    db = DatabaseManager(database_url=DATABASE_URL, logger_name="scraper.db")

    redis_client = RedisClient(
        host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, password=REDIS_PASSWORD,
    )
    await redis_client.connect_with_retry(
        retries=STARTUP_RETRIES, delay=STARTUP_RETRY_DELAY,
    )
    deduplicator = JobDeduplicator(redis_client.get_client())

    service = ScraperService(rabbitmq=rabbitmq, db=db, deduplicator=deduplicator)
    await service.run()


if __name__ == "__main__":
    asyncio.run(main())
