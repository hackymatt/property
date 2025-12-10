"""Core scheduler implementation"""

import asyncio
from datetime import datetime, timezone
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from croniter import croniter
from src.models import Schedule, Job
from src.database import DatabaseManager
from src.logger import logger
from config import CHECK_INTERVAL


class Scheduler:
    """Async scheduler that checks database every second"""

    def __init__(self):
        self.db = DatabaseManager()
        self.check_interval = CHECK_INTERVAL
        self.running = False

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
                   'status': 'pending',
                   'jobs': [{'source': job.source,
                             'stage': job.stage,
                             'url': job.url,
                             'domain': job.domain.name} for job in schedule.jobs]}

        logger.info(f"Schedule payload: {payload}")

    def calculate_next_run(self, cron_expression: str) -> datetime:
        """Calculate next run time using croniter"""
        try:
            # Use naive datetime since database column is TIMESTAMP WITHOUT TIME ZONE
            cron = croniter(cron_expression, datetime.now(timezone.utc).replace(tzinfo=None))
            next_time = cron.get_next(datetime)
            return next_time
        except (ValueError, AttributeError) as e:
            logger.error(f"Invalid cron expression '{cron_expression}': {e}")
            return None

    async def run(self):
        """Main scheduler loop - checks database every N seconds"""
        await self.db.init()
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
                            next_run = self.calculate_next_run(schedule.cron)
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
            await self.db.close()

    def stop(self):
        """Stop the scheduler"""
        self.running = False
