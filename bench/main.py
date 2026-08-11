import asyncio

from config import (
    DATABASE_URL,
    RABBITMQ_HOST,
    RABBITMQ_PASSWORD,
    RABBITMQ_PORT,
    RABBITMQ_USER,
    RABBITMQ_VHOST,
    STARTUP_RETRIES,
    STARTUP_RETRY_DELAY,
)
from shared.database import DatabaseManager
from shared.rabbitmq import RabbitMQClient
from src import models
from src.logger import logger
from src.orchestrator import OrchestratorService


async def main():
    db = DatabaseManager(database_url=DATABASE_URL, logger_name="bench")
    await db.init(retries=STARTUP_RETRIES, delay=STARTUP_RETRY_DELAY)
    await db.reflect_models(models.Base)
    models.ScraperSource = models.Base.classes.scraper_source
    models.ScraperSourceStage = models.Base.classes.scraper_source_stage
    models.JobRunLog = models.Base.classes.jobrunlog
    logger.info("Database initialized and models reflected")

    rabbitmq = RabbitMQClient(
        host=RABBITMQ_HOST,
        port=RABBITMQ_PORT,
        username=RABBITMQ_USER,
        password=RABBITMQ_PASSWORD,
        virtual_host=RABBITMQ_VHOST,
    )
    await rabbitmq.connect_with_retry(retries=STARTUP_RETRIES, delay=STARTUP_RETRY_DELAY, logger=logger)

    service = OrchestratorService(rabbitmq=rabbitmq, db=db)
    await asyncio.gather(
        service.run_schedule_consumer(),
        service.run_job_status_consumer(),
    )


if __name__ == "__main__":
    asyncio.run(main())
