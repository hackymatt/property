"""
Async Scheduler Service
Monitors the schedule table and executes schedules based on next_run column.
Checks database every N seconds for schedules to run.
"""

import asyncio

from src.scheduler import Scheduler
from src.logger import logger


async def main():
    """Entry point for the scheduler"""
    logger.info("Starting scheduler service...")
    
    scheduler = Scheduler()

    try:
        await scheduler.run()
    except Exception as e:
        logger.critical(f"Failed to start scheduler: {e}", exc_info=True)
        raise


if __name__ == '__main__':
    asyncio.run(main())
