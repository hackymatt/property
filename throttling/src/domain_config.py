"""
Domain Configuration Manager
Loads and caches domain-specific throttling configurations from the database.
"""

import asyncio
from typing import Dict, Optional
from sqlalchemy import select

from src.models import Domain
from src.logger import logger
from config import (
    DEFAULT_REQUESTS_PER_SECOND,
    DEFAULT_CONCURRENT_REQUESTS,
    CONFIG_REFRESH_INTERVAL,
)


class DomainConfig:
    """Manages domain-specific throttling configurations."""

    def __init__(self, db_session_factory):
        """
        Initialize domain config manager.

        Args:
            db_session_factory: SQLAlchemy async session factory
        """
        self.db_session_factory = db_session_factory
        self._config_cache: Dict[str, dict] = {}
        self._cache_lock = asyncio.Lock()
        self._refresh_task: Optional[asyncio.Task] = None
        logger.info("DomainConfig initialized")

    async def start(self):
        """Start the config refresh background task."""
        await self.refresh_configs()
        self._refresh_task = asyncio.create_task(self._refresh_loop())
        logger.info("Config refresh task started")

    async def stop(self):
        """Stop the config refresh background task."""
        if self._refresh_task:
            self._refresh_task.cancel()
            try:
                await self._refresh_task
            except asyncio.CancelledError:
                pass
        logger.info("Config refresh task stopped")

    async def _refresh_loop(self):
        """Background task to refresh configs periodically."""
        while True:
            try:
                await asyncio.sleep(CONFIG_REFRESH_INTERVAL)
                await self.refresh_configs()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in config refresh loop: {e}", exc_info=True)

    async def refresh_configs(self):
        """Refresh all domain configurations from the database."""
        try:
            async with self.db_session_factory() as session:
                result = await session.execute(
                    select(Domain).where(Domain.is_active == True)
                )
                domains = result.scalars().all()

                new_cache = {}
                for domain in domains:
                    new_cache[domain.name] = {
                        "requests_per_second": domain.requests_per_second,
                        "burst_capacity": domain.burst_capacity,
                        "concurrent_requests": domain.concurrent_requests,
                        "max_retries": domain.max_retries,
                        "retry_delay": domain.retry_delay,
                    }

                async with self._cache_lock:
                    self._config_cache = new_cache

                logger.info(f"Refreshed configs for {len(new_cache)} domains")

        except Exception as e:
            logger.error(f"Failed to refresh domain configs: {e}", exc_info=True)

    async def get_config(self, domain: str) -> dict:
        """
        Get throttling configuration for a domain.
        Returns default config if domain not found.

        Args:
            domain: Domain name

        Returns:
            Dictionary with throttling configuration
        """
        async with self._cache_lock:
            config = self._config_cache.get(domain)

        if config:
            return config
        else:
            # Return default config if domain not found
            logger.debug(f"Using default config for domain: {domain}")
            return {
                "requests_per_second": DEFAULT_REQUESTS_PER_SECOND,
                "burst_capacity": 2,
                "concurrent_requests": DEFAULT_CONCURRENT_REQUESTS,
                "max_retries": 3,
                "retry_delay": 5.0,
            }

    async def get_all_configs(self) -> Dict[str, dict]:
        """Get all cached domain configurations."""
        async with self._cache_lock:
            return self._config_cache.copy()
