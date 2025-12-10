import sys
import asyncio

from src.logger import logger
from config import (
    RABBITMQ_HOST,
    RABBITMQ_PORT,
    RABBITMQ_USER,
    RABBITMQ_PASSWORD,
    RABBITMQ_VHOST
)
from shared.rabbitmq import RabbitMQClient
from src.service import ScheduleLoggerService


def main():
    try:
        rabbitmq = RabbitMQClient(
            host=RABBITMQ_HOST,
            port=RABBITMQ_PORT,
            username=RABBITMQ_USER or None,
            password=RABBITMQ_PASSWORD or None,
            virtual_host=RABBITMQ_VHOST,
        )
        service = ScheduleLoggerService(rabbitmq=rabbitmq)
        asyncio.run(service.run())
    except KeyboardInterrupt:
        logger.warning("Logger interrupted by user")
    except Exception as exc:
        logger.critical(f"Logger terminated: {exc}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
