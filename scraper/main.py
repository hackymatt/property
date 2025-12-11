import asyncio
from config import (
    RABBITMQ_HOST,
    RABBITMQ_PORT,
    RABBITMQ_USER,
    RABBITMQ_PASSWORD,
    RABBITMQ_VHOST,
)
from shared.rabbitmq import RabbitMQClient
from src.service import ScraperService


async def main():
    """Main entry point - starts scraper service listening to job queue"""
    rabbitmq = RabbitMQClient(
        host=RABBITMQ_HOST,
        port=RABBITMQ_PORT,
        username=RABBITMQ_USER,
        password=RABBITMQ_PASSWORD,
        virtual_host=RABBITMQ_VHOST,
    )
    service = ScraperService(rabbitmq=rabbitmq)
    await service.run()


if __name__ == "__main__":
    asyncio.run(main())
