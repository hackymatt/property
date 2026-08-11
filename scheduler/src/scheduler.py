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
    RABBITMQ_SCHEDULE_EXCHANGE,
    RABBITMQ_EXCHANGE_TYPE,
    DATABASE_URL,
)
from shared.cron_utils import calculate_next_run
from shared.consts import Status
from shared.payloads import SchedulePayload, JobPayload
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

    async def claim_schedules_to_run(self) -> list:
        """Atomically fetch and advance next_run for schedules due to run.

        Uses SELECT FOR UPDATE SKIP LOCKED so concurrent scheduler replicas
        never process the same schedule in the same tick.
        """
        async with self.db.get_session() as session:
            async with session.begin():
                now = datetime.now(timezone.utc).replace(tzinfo=None)
                stmt = (
                    select(models.Schedule)
                    .where(
                        and_(
                            models.Schedule.is_active == True,
                            models.Schedule.next_run <= now,
                        )
                    )
                    .with_for_update(skip_locked=True)
                )
                result = await session.execute(stmt)
                schedules = result.scalars().all()

                # Advance next_run inside the same transaction so the lock
                # prevents any other instance from picking up the same schedule.
                for schedule in schedules:
                    next_run = calculate_next_run(schedule.cron)
                    if next_run:
                        await session.execute(
                            models.Schedule.__table__.update()
                            .where(models.Schedule.id == schedule.id)
                            .values(next_run=next_run)
                        )

                # Return copies of the data we need; session closes after this block.
                return [
                    {
                        "id": s.id,
                        "name": s.name,
                        "cron": s.cron,
                    }
                    for s in schedules
                ]

    # === Job/Domain data loading ===

    async def _get_job_ids_for_schedule(self, schedule_id: int) -> list[int]:
        async with self.db.get_session() as session:
            result = await session.execute(
                text("SELECT job_id FROM schedule_jobs WHERE schedule_id = :schedule_id"),
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
                        "id": job.id,
                        "source": job.source,
                        "stage": job.stage,
                        "url": job.url,
                        "params": job.params or {},
                        "domain": domain.name if domain else None,
                    }
                )

        return jobs_data

    # === Publishing ===

    async def _build_schedule_payload(self, schedule: dict) -> SchedulePayload:
        job_ids = await self._get_job_ids_for_schedule(schedule["id"])
        jobs_data = await self._get_jobs_with_domains(job_ids)

        jobs_payload = [
            JobPayload(
                parent_job_run_id=None,
                source=job["source"],
                stage=job["stage"],
                url=job["url"],
                domain_name=job["domain"],
                params=job["params"],
            )
            for job in jobs_data
        ]

        return SchedulePayload(
            schedule_id=schedule["id"],
            jobs=jobs_payload,
        )

    async def _publish_schedule(self, payload: SchedulePayload):
        """Publish schedule payload to exchange with routing key schedule.{schedule_run_id}.{status}"""
        if not self.rabbitmq:
            logger.warning("RabbitMQ not available; skipping publish")
            return

        message = payload.model_dump()
        schedule_run_id = str(uuid.uuid4())
        routing_key = f"schedule.{schedule_run_id}.{Status.PENDING}"

        try:
            await self.rabbitmq.publish_to_exchange(
                exchange=RABBITMQ_SCHEDULE_EXCHANGE,
                routing_key=routing_key,
                message=message,
                exchange_type=RABBITMQ_EXCHANGE_TYPE,
            )
            logger.info(
                "Published schedule payload %s to exchange %s with routing_key %s",
                message,
                RABBITMQ_SCHEDULE_EXCHANGE,
                routing_key,
            )
        except Exception as exc:
            logger.error(f"Failed to publish schedule payload: {exc}", exc_info=True)

    # === Main scheduler loop ===

    async def process_schedule(self, schedule: dict):
        """Process a single schedule dict: build payload and publish to queue."""
        logger.info("Processing schedule: %s", schedule["name"])
        payload = await self._build_schedule_payload(schedule)
        await self._publish_schedule(payload)

    async def _process_scheduled_runs(self):
        """Claim and process all schedules due to run.

        next_run is advanced inside claim_schedules_to_run (same transaction as
        the SELECT FOR UPDATE), so publishing happens after the lock is released.
        """
        schedules = await self.claim_schedules_to_run()

        if not schedules:
            return

        logger.info("Found %d schedule(s) to run", len(schedules))
        for schedule in schedules:
            try:
                await self.process_schedule(schedule)
            except Exception as e:
                logger.error("Error processing schedule %s: %s", schedule["id"], e, exc_info=True)

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
