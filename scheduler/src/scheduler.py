"""Core scheduler implementation"""

import asyncio
import uuid
from datetime import datetime, timezone
from sqlalchemy import select, and_, text
from src import models
from src.logger import logger
from config import (
    CHECK_INTERVAL,
    STARTUP_RETRIES,
    STARTUP_RETRY_DELAY,
    RABBITMQ_HOST,
    RABBITMQ_PORT,
    RABBITMQ_USER,
    RABBITMQ_PASSWORD,
    RABBITMQ_VHOST,
    RABBITMQ_SCHEDULE_QUEUE,
    DATABASE_URL,
)
from shared.cron_utils import calculate_next_run
from shared.consts import Status
from shared.rabbitmq import RabbitMQClient
from shared.database import DatabaseManager


class Scheduler:
    """Async scheduler that checks database every N seconds and publishes schedules to queue"""

    def __init__(self):
        self.db = DatabaseManager(database_url=DATABASE_URL, logger_name="scheduler")
        self.check_interval = CHECK_INTERVAL
        self.running = False
        self.rabbitmq = RabbitMQClient(
            host=RABBITMQ_HOST,
            port=RABBITMQ_PORT,
            username=RABBITMQ_USER or None,
            password=RABBITMQ_PASSWORD or None,
            virtual_host=RABBITMQ_VHOST,
        )

    # === Initialization ===

    async def startup(self):
        """Initialize database, RabbitMQ, and reflect models"""
        await self._init_database()
        await self._init_rabbitmq()

    async def _init_database(self):
        """Initialize database connection and reflect models from schema"""
        await self.db.init(retries=STARTUP_RETRIES, delay=STARTUP_RETRY_DELAY)
        await self.db.reflect_models(models.Base)
        models.Schedule = models.Base.classes.schedule
        models.Job = models.Base.classes.job
        models.Domain = models.Base.classes.domain
        logger.info("Database initialized and models reflected")

    async def _init_rabbitmq(self):
        """Initialize RabbitMQ connection"""
        await self.rabbitmq.connect_with_retry(
            retries=STARTUP_RETRIES,
            delay=STARTUP_RETRY_DELAY,
            logger=logger,
        )
        logger.info("RabbitMQ connected")

    # === Database queries ===

    async def get_schedules_to_run(self) -> list:
        """Fetch schedules that should run now (next_run <= now and is_active = True)"""
        async with self.db.get_session() as session:
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            stmt = select(models.Schedule).where(
                and_(
                    models.Schedule.is_active == True,
                    models.Schedule.next_run <= now,
                )
            )
            result = await session.execute(stmt)
            return result.scalars().all()

    async def update_next_run(self, schedule_id: int, new_next_run: datetime):
        """Update the next_run timestamp for a schedule"""
        async with self.db.get_session() as session:
            stmt = select(models.Schedule).where(models.Schedule.id == schedule_id)
            result = await session.execute(stmt)
            db_schedule = result.scalar_one_or_none()
            if db_schedule:
                db_schedule.next_run = new_next_run
                await session.commit()

    # === Job/Domain data loading ===

    async def _get_job_ids_for_schedule(self, schedule_id: int) -> list[int]:
        """Fetch job IDs associated with a schedule via junction table"""
        async with self.db.get_session() as session:
            result = await session.execute(
                text(
                    "SELECT job_id FROM schedule_jobs WHERE schedule_id = :schedule_id"
                ),
                {"schedule_id": schedule_id},
            )
            return [row[0] for row in result.fetchall()]

    async def _get_domain_for_job(self, session, domain_id: int):
        """Fetch domain by ID"""
        domain_result = await session.execute(
            select(models.Domain).where(models.Domain.id == domain_id)
        )
        return domain_result.scalar_one_or_none()

    async def _get_jobs_with_domains(self, job_ids: list[int]) -> list[dict]:
        """Fetch job details with domain names"""
        if not job_ids:
            return []

        jobs_data = []
        async with self.db.get_session() as session:
            jobs_result = await session.execute(
                select(models.Job).where(models.Job.id.in_(job_ids))
            )
            jobs = jobs_result.scalars().all()

            for job in jobs:
                domain = await self._get_domain_for_job(session, job.domain_id)
                jobs_data.append(
                    {
                        "source": job.source,
                        "stage": job.stage,
                        "url": job.url,
                        "domain": domain.name if domain else None,
                    }
                )

        return jobs_data

    # === Publishing ===

    async def _build_schedule_payload(self, schedule) -> dict:
        """Build payload for a schedule including jobs and domains"""
        job_ids = await self._get_job_ids_for_schedule(schedule.id)
        jobs_data = await self._get_jobs_with_domains(job_ids)

        return {
            "run_id": str(uuid.uuid4()),
            "schedule_id": schedule.id,
            "status": Status.PENDING,
            "jobs": jobs_data,
        }

    async def _publish_schedule(self, payload: dict):
        """Publish schedule payload to RabbitMQ queue"""
        if not self.rabbitmq:
            logger.warning("RabbitMQ not available; skipping publish")
            return

        try:
            await self.rabbitmq.publish(queue=RABBITMQ_SCHEDULE_QUEUE, message=payload)
            logger.info(f"Published schedule payload {payload} to queue")
        except Exception as exc:
            logger.error(f"Failed to publish schedule payload: {exc}", exc_info=True)

    # === Main scheduler loop ===

    async def process_schedule(self, schedule):
        """Process a single schedule: build payload and publish to queue"""
        logger.info(f"Processing schedule: {schedule.name}")
        payload = await self._build_schedule_payload(schedule)
        await self._publish_schedule(payload)

    async def _process_scheduled_runs(self):
        """Fetch and process all schedules that need to run"""
        schedules = await self.get_schedules_to_run()

        if not schedules:
            return

        logger.info(f"Found {len(schedules)} schedule(s) to run")
        for schedule in schedules:
            try:
                await self.process_schedule(schedule)
                # Calculate and update next run time
                next_run = calculate_next_run(schedule.cron)
                if next_run:
                    await self.update_next_run(schedule.id, next_run)
            except Exception as e:
                logger.error(
                    f"Error processing schedule {schedule.id}: {e}", exc_info=True
                )

    def _handle_loop_error(self, error: Exception, table_error_logged: bool) -> bool:
        """Handle errors in scheduler loop, return True if table error"""
        error_str = str(error)
        if "does not exist" in error_str or "UndefinedTableError" in error_str:
            if not table_error_logged:
                logger.warning(
                    "Schedule table not found. Waiting for database migrations..."
                )
            return True
        else:
            logger.error(f"Error in scheduler loop: {error}", exc_info=True)
            return False

    async def run(self):
        """Main scheduler loop"""
        await self.startup()

        self.running = True
        logger.info(
            f"Scheduler started, checking database every {self.check_interval} second(s)"
        )
        table_error_logged = False

        try:
            while self.running:
                try:
                    await self._process_scheduled_runs()
                    table_error_logged = False
                    await asyncio.sleep(self.check_interval)
                except Exception as e:
                    table_error_logged = self._handle_loop_error(e, table_error_logged)
                    await asyncio.sleep(self.check_interval)

        except KeyboardInterrupt:
            logger.warning("Scheduler interrupted by user")
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
        finally:
            await self.shutdown()

    async def shutdown(self):
        """Close all connections"""
        if self.rabbitmq:
            try:
                await self.rabbitmq.close()
            except Exception as e:
                logger.warning(f"Error closing RabbitMQ: {e}")
        await self.db.close()
        logger.info("Scheduler shutdown complete")

    def stop(self):
        """Signal scheduler to stop"""
        self.running = False
        logger.info("Stop signal sent to scheduler")
