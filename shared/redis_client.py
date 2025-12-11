"""Shared Redis client for distributed state management"""

import asyncio
from typing import Optional

import redis.asyncio as redis


class RedisClient:
    """Manages async Redis connections"""

    def __init__(
        self,
        host: str = "redis",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        decode_responses: bool = True,
    ):
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.decode_responses = decode_responses
        self.client: Optional[redis.Redis] = None

    async def connect(self):
        """Initialize Redis connection"""
        self.client = redis.Redis(
            host=self.host,
            port=self.port,
            db=self.db,
            password=self.password,
            decode_responses=self.decode_responses,
        )
        await self.client.ping()

    async def connect_with_retry(self, retries: int, delay: int, logger=None):
        """Connect to Redis with retry logic"""
        for attempt in range(1, retries + 1):
            try:
                await self.connect()
                if logger:
                    logger.info("Connected to Redis")
                return
            except Exception as exc:
                if attempt == retries:
                    if logger:
                        logger.error(
                            f"Redis connection failed after {attempt} attempt(s): {exc} "
                            f"[host={self.host}]"
                        )
                    raise
                if logger:
                    logger.warning(
                        f"Redis connection failed (attempt {attempt}/{retries}): {exc}. "
                        f"Retrying in {delay}s... [host={self.host}]"
                    )
                await asyncio.sleep(delay)

    async def close(self):
        """Close Redis connection"""
        if self.client:
            await self.client.close()

    def get_client(self) -> redis.Redis:
        """Get the Redis client instance"""
        if not self.client:
            raise RuntimeError("Redis client is not connected. Call connect() first.")
        return self.client
