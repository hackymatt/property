"""Loads ScraperSource configs from the database with a TTL cache."""

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.automap import automap_base

from src.logger import logger


@dataclass
class SourceConfig:
    name: str
    domain_name: str
    offer_url_prefix: str
    preamble_code: str
    list_pages_code: str
    list_items_code: str
    get_item_code: str


class SourceLoader:
    REFRESH_INTERVAL = timedelta(minutes=5)

    def __init__(self, db):
        self.db = db
        self._cache: dict[str, SourceConfig] = {}
        self._last_refresh: Optional[datetime] = None
        self._lock = asyncio.Lock()
        self._base = None

    async def init(self):
        self._base = automap_base()
        await self.db.reflect_models(self._base)
        await self._refresh()
        logger.info("[SourceLoader] Loaded %d source(s) from database", len(self._cache))

    async def get(self, name: str) -> Optional[SourceConfig]:
        await self._maybe_refresh()
        config = self._cache.get(name)
        if config is None:
            logger.warning("[SourceLoader] Source '%s' not found in cache (active sources: %s)", name, list(self._cache))
        return config

    async def _maybe_refresh(self):
        now = datetime.utcnow()
        if self._last_refresh and now - self._last_refresh < self.REFRESH_INTERVAL:
            return
        async with self._lock:
            if self._last_refresh and now - self._last_refresh < self.REFRESH_INTERVAL:
                return
            await self._refresh()

    async def _refresh(self):
        try:
            ScraperSource = self._base.classes.scraper_source
            Domain = self._base.classes.domain
        except AttributeError:
            logger.warning("[SourceLoader] scraper_source table not yet available — skipping refresh")
            self._last_refresh = datetime.utcnow()
            return

        try:
            async with self.db.get_session() as session:
                rows = (
                    await session.execute(
                        select(ScraperSource, Domain)
                        .join(Domain, ScraperSource.domain_id == Domain.id)
                        .where(ScraperSource.is_active.is_(True))
                    )
                ).all()

            self._cache = {
                r.scraper_source.name: SourceConfig(
                    name=r.scraper_source.name,
                    domain_name=r.domain.name,
                    offer_url_prefix=r.scraper_source.offer_url_prefix or "",
                    preamble_code=r.scraper_source.preamble_code or "",
                    list_pages_code=r.scraper_source.list_pages_code,
                    list_items_code=r.scraper_source.list_items_code,
                    get_item_code=r.scraper_source.get_item_code,
                )
                for r in rows
            }
            self._last_refresh = datetime.utcnow()
            logger.info("[SourceLoader] Refreshed — %d active source(s)", len(self._cache))
        except Exception:
            logger.exception("[SourceLoader] Failed to refresh sources from database")
