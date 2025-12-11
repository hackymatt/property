"""
Async Throttling Service
Provides rate limiting and throttling for web scraping based on per-domain configuration.
Implements token bucket algorithm with distributed state using Redis.
"""

import asyncio

from src.throttle_service import ThrottleService
from src.logger import logger


async def main():
    """Entry point for the throttling service"""
    logger.info("Starting throttling service...")

    service = ThrottleService()

    try:
        await service.run()
    except Exception as e:
        logger.critical(f"Failed to start throttling service: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())
