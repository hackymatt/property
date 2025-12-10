"""Shared async DatabaseManager for services"""

from typing import Optional

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

from shared.logger import get_logger


class DatabaseManager:
    """Manages async database connections"""

    def __init__(self, database_url: str, logger_name: str = "db"):
        self.database_url = database_url
        self.engine: Optional[object] = None
        self.async_session: Optional[sessionmaker] = None
        self.logger = get_logger(logger_name)

    async def _init(self):
        """Initialize async engine and session factory"""
        try:
            self.engine = create_async_engine(
                self.database_url,
                echo=False,
                pool_pre_ping=True,
                pool_size=5,
                max_overflow=10,
            )
            self.async_session = sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autocommit=False,
                autoflush=False,
            )
            self.logger.info("Database connection initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}", exc_info=True)
            raise

    async def reflect_models(self, base_class):
        """Reflect ORM models from database schema. Call after _init()."""
        if not self.engine:
            raise RuntimeError("Engine not initialized. Call _init() first.")
        async with self.engine.begin() as conn:
            await conn.run_sync(base_class.prepare, reflect=True)

    async def _test_connection(self):
        """Execute a lightweight test query to verify connectivity"""
        if not self.engine:
            raise RuntimeError("Database engine not initialized")
        async with self.engine.connect() as conn:
            await conn.execute(text("SELECT 1"))

    async def close(self):
        """Close database connection"""
        try:
            if self.engine:
                await self.engine.dispose()
            self.logger.info("Database connection closed")
        except Exception as e:
            self.logger.error(f"Error closing database connection: {e}", exc_info=True)

    def get_session(self):
        """Get a new async session"""
        if not self.async_session:
            raise RuntimeError("Database not initialized. Call init() first.")
        return self.async_session()

    async def init(self, retries: int = 5, delay: int = 5):
        """Initialize database with retries; raises if unreachable."""
        import asyncio

        for attempt in range(1, retries + 1):
            try:
                await self._init()
                await self._test_connection()
                self.logger.info("Database reachable")
                return
            except Exception as exc:
                if attempt == retries:
                    self.logger.error(
                        f"Database connection failed after {attempt} attempt(s): {exc}"
                    )
                    raise
                self.logger.warning(
                    f"Database connection failed (attempt {attempt}/{retries}): {exc}. "
                    f"Retrying in {delay}s..."
                )
                await asyncio.sleep(delay)
