"""Core scheduler implementation"""

import asyncio
import time
from datetime import datetime, timezone
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from src.models import Schedule, Job
from src.database import DatabaseManager
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
)
from shared.cron_utils import calculate_next_run
from shared.consts import Status
from shared.rabbitmq import RabbitMQClient


class Scheduler:
    """Async scheduler that checks database every second"""

    def __init__(self):
        self.db = DatabaseManager()
        self.check_interval = CHECK_INTERVAL
        self.running = False
        self.rabbitmq = RabbitMQClient(
            host=RABBITMQ_HOST,
            port=RABBITMQ_PORT,
            username=RABBITMQ_USER or None,
            password=RABBITMQ_PASSWORD or None,
            virtual_host=RABBITMQ_VHOST,
        )

    async def get_schedules_to_run(self) -> list[Schedule]:
        """
        Fetch schedules that should run now
        Returns schedules where next_run <= now and is_active = True
        """
        async with self.db.get_session() as session:
            # Use naive datetime since database column is TIMESTAMP WITHOUT TIME ZONE
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            stmt = select(Schedule).options(
                selectinload(Schedule.jobs).selectinload(Job.domain)
            ).where(
                and_(
                    Schedule.is_active == True,
                    Schedule.next_run <= now,
                )
            )
            result = await session.execute(stmt)
            return result.scalars().all()

    async def update_next_run(self, schedule_id: int, new_next_run: datetime):
        """Update the next_run timestamp for a schedule"""
        async with self.db.get_session() as session:
            stmt = select(Schedule).where(Schedule.id == schedule_id)
            result = await session.execute(stmt)
            db_schedule = result.scalar_one_or_none()

            if db_schedule:
                db_schedule.next_run = new_next_run
                await session.commit()

    async def process_schedule(self, schedule: Schedule):
        """Process a single schedule"""
        logger.info(f"Running schedule: {schedule.name}")
        
        payload = {'schedule_id': schedule.id,
                   'status': Status.PENDING,
                   'jobs': [{'source': job.source,
                             'stage': job.stage,
                             'url': job.url,
                             'domain': job.domain.name} for job in schedule.jobs]}

        # Publish to schedule queue if RabbitMQ is available
        if self.rabbitmq:
            try:
                self.rabbitmq.publish(queue=RABBITMQ_SCHEDULE_QUEUE, message=payload)
                logger.info(f"Published schedule payload {payload} to queue '{RABBITMQ_SCHEDULE_QUEUE}'")
            except Exception as exc:
                logger.error(f"Failed to publish schedule payload {payload}: {exc}")

    async def run(self):
        """Main scheduler loop - checks database every N seconds"""
        # Startup checks: ensure DB and RabbitMQ are reachable
        await self._init_db_with_retry()
        self._init_rabbit_with_retry()

        self.running = True
        logger.info(f"Scheduler started, checking database every {self.check_interval} second(s)")
        table_error_logged = False

        try:
            while self.running:
                try:
                    # Get schedules that need to run
                    schedules = await self.get_schedules_to_run()

                    if schedules:
                        logger.info(f"Found {len(schedules)} schedule(s) to run")
                        for schedule in schedules:
                            await self.process_schedule(schedule)
                            # Calculate next run time based on cron expression
                            next_run = calculate_next_run(schedule.cron)
                            if next_run:
                                await self.update_next_run(schedule.id, next_run)
                    
                    # Reset error flag if query succeeds
                    table_error_logged = False

                    # Wait N seconds before checking again
                    await asyncio.sleep(self.check_interval)

                except Exception as e:
                    error_str = str(e)
                    # Check if it's a table not found error
                    if "does not exist" in error_str or "UndefinedTableError" in error_str:
                        if not table_error_logged:
                            logger.warning("Schedule table not found. Waiting for database migrations to complete...")
                            table_error_logged = True
                    else:
                        logger.error(f"Error in scheduler loop: {e}", exc_info=True)
                    
                    await asyncio.sleep(self.check_interval)  # Don't spam errors

        except KeyboardInterrupt:
            logger.warning("Scheduler interrupted by user")
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
        finally:
            if self.rabbitmq:
                try:
                    self.rabbitmq.close()
                except Exception:
                    pass
            await self.db.close()

    async def _init_db_with_retry(self):
        """Init DB engine and verify connectivity with retries"""
        for attempt in range(1, STARTUP_RETRIES + 1):
            try:
                await self.db.init()
                await self.db.test_connection()
                logger.info("Database reachable")
                return
            except Exception as exc:
                if attempt == STARTUP_RETRIES:
                    logger.error(f"Database connection failed after {attempt} attempt(s): {exc}")
                    raise
                logger.warning(
                    f"Database connection failed (attempt {attempt}/{STARTUP_RETRIES}): {exc}. "
                    f"Retrying in {STARTUP_RETRY_DELAY}s..."
                )
                await asyncio.sleep(STARTUP_RETRY_DELAY)

    def _init_rabbit_with_retry(self):
        """Init RabbitMQ connection with retries; raise if unreachable"""
        for attempt in range(1, STARTUP_RETRIES + 1):
            try:
                self.rabbitmq.connect()
                logger.info("Connected to RabbitMQ")
                return
            except Exception as exc:
                if attempt == STARTUP_RETRIES:
                    logger.error(
                        f"RabbitMQ connection failed after {attempt} attempt(s): {exc} "
                        f"[host={RABBITMQ_HOST} user={RABBITMQ_USER}]"
                    )
                    raise
                logger.warning(
                    f"RabbitMQ connection failed (attempt {attempt}/{STARTUP_RETRIES}): {exc}. "
                    f"Retrying in {STARTUP_RETRY_DELAY}s... [host={RABBITMQ_HOST} user={RABBITMQ_USER}]"
                )
                time.sleep(STARTUP_RETRY_DELAY)

    def stop(self):
        """Stop the scheduler"""
        self.running = False
