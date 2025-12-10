"""Database connection and session management"""

from typing import Optional
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from src.logger import logger
from config import DATABASE_URL


class DatabaseManager:
    """Manages async database connections"""

    def __init__(self):
        self.database_url = DATABASE_URL
        self.engine: Optional[object] = None
        self.async_session: Optional[sessionmaker] = None

    async def init(self):
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
            logger.info("Database connection initialized")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}", exc_info=True)
            raise

    async def test_connection(self):
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
            logger.info("Database connection closed")
        except Exception as e:
            logger.error(f"Error closing database connection: {e}", exc_info=True)

    def get_session(self):
        """Get a new async session"""
        if not self.async_session:
            raise RuntimeError("Database not initialized. Call init() first.")
        return self.async_session()
