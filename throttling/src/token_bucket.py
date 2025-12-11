"""
Token Bucket Algorithm Implementation for Rate Limiting
Implements a distributed token bucket using Redis for state management.
"""

import time
import asyncio
from urllib.parse import urlparse

from src.logger import logger


class TokenBucket:
    """
    Distributed token bucket rate limiter using Redis.

    This implementation uses the token bucket algorithm which is more lenient
    than fixed-window rate limiting and allows for burst traffic while maintaining
    average rate limits.

    Key features:
    - Tokens are added at a constant rate (refill_rate)
    - Bucket has a maximum capacity (max_tokens)
    - Each request consumes one token
    - Requests wait if no tokens are available
    - Uses Redis for distributed state across multiple service instances
    """

    def __init__(
        self,
        redis_client,
        domain: str,
        refill_rate: float,  # tokens per second
        max_tokens: int,
        concurrent_limit: int = 1,
    ):
        """
        Initialize token bucket for a domain.

        Args:
            redis_client: Redis client from shared.redis_client
            domain: Domain name for this bucket
            refill_rate: Number of tokens added per second
            max_tokens: Maximum number of tokens in bucket
            concurrent_limit: Maximum concurrent requests allowed
        """
        self.redis_client = redis_client
        self.domain = domain
        self.refill_rate = refill_rate
        self.max_tokens = max_tokens
        self.concurrent_limit = concurrent_limit

        # Redis keys
        self.tokens_key = f"throttle:tokens:{domain}"
        self.timestamp_key = f"throttle:timestamp:{domain}"
        self.concurrent_key = f"throttle:concurrent:{domain}"
        self.lock_key = f"throttle:lock:{domain}"

        logger.debug(
            f"TokenBucket initialized for {domain}: "
            f"rate={refill_rate}/s, max={max_tokens}, concurrent={concurrent_limit}"
        )

    async def acquire(self, timeout: float = None) -> bool:
        """
        Acquire a token to make a request to this domain.
        Waits until a token is available or timeout is reached.

        Args:
            timeout: Maximum time to wait for a token (seconds). None or 0 = wait indefinitely

        Returns:
            True if token acquired, False if timeout reached
        """
        logger.info(f"[ACQUIRE] Starting acquire for {self.domain}")
        start_time = time.time()

        while True:
            # Check timeout if specified
            if timeout and timeout > 0:
                if time.time() - start_time >= timeout:
                    logger.warning(f"Timeout waiting for token for {self.domain}")
                    return False

            # Check concurrent request limit
            logger.info(f"[ACQUIRE] Checking concurrent count for {self.domain}")
            concurrent_count = await self._get_concurrent_count()
            logger.info(
                f"[ACQUIRE] Concurrent count for {self.domain}: {concurrent_count}/{self.concurrent_limit}"
            )
            if concurrent_count >= self.concurrent_limit:
                logger.debug(
                    f"Concurrent limit reached for {self.domain} "
                    f"({concurrent_count}/{self.concurrent_limit}), waiting..."
                )
                await asyncio.sleep(0.1)
                continue

            # Try to acquire a token
            if await self._try_acquire():
                try:
                    # Increment concurrent counter - wrapped in try-except for robustness
                    await self.redis_client.incr(self.concurrent_key)
                    await self.redis_client.expire(
                        self.concurrent_key, 300
                    )  # 5 min TTL
                    logger.debug(f"Token acquired for {self.domain}")
                    return True
                except Exception as e:
                    logger.error(
                        f"Error incrementing concurrent counter for {self.domain}: {e}. "
                        f"Will proceed anyway but counter may be out of sync.",
                        exc_info=True,
                    )
                    # Still return True since token was acquired, just counter update failed
                    return True

            # Calculate wait time
            wait_time = 1.0 / self.refill_rate if self.refill_rate > 0 else 1.0
            await asyncio.sleep(min(wait_time, 0.5))

    async def release(self):
        """Release a token after request completes (decrement concurrent counter).

        Gracefully handles errors to prevent counter from getting out of sync.
        """
        try:
            count = await self._get_concurrent_count()
            if count > 0:
                await self.redis_client.decr(self.concurrent_key)
                logger.debug(f"Token released for {self.domain}")
            else:
                logger.warning(
                    f"Attempted to release token for {self.domain} but concurrent count is already 0. "
                    f"Counter may be out of sync."
                )
        except Exception as e:
            logger.error(f"Error releasing token for {self.domain}: {e}", exc_info=True)

    async def _try_acquire(self) -> bool:
        """
        Try to acquire a token using the token bucket algorithm.
        Updates token count based on time elapsed.

        Returns:
            True if token acquired, False otherwise
        """
        now = time.time()

        # Get current state
        tokens_str = await self.redis_client.get(self.tokens_key)
        timestamp_str = await self.redis_client.get(self.timestamp_key)

        # Initialize if first time
        if tokens_str is None or timestamp_str is None:
            tokens = float(self.max_tokens)
            last_refill = now
        else:
            tokens = float(tokens_str)
            last_refill = float(timestamp_str)

        # Calculate tokens to add based on time elapsed
        time_elapsed = now - last_refill
        tokens_to_add = time_elapsed * self.refill_rate
        tokens = min(self.max_tokens, tokens + tokens_to_add)

        # Try to consume a token
        if tokens >= 1.0:
            tokens -= 1.0

            # Update state in Redis
            await self.redis_client.set(
                self.tokens_key, str(tokens), ex=3600
            )  # 1 hour TTL
            await self.redis_client.set(self.timestamp_key, str(now), ex=3600)

            return True
        else:
            # Not enough tokens, update refill timestamp
            await self.redis_client.set(self.timestamp_key, str(now), ex=3600)
            return False

    async def _get_concurrent_count(self) -> int:
        """Get current concurrent request count."""
        count_str = await self.redis_client.get(self.concurrent_key)
        return int(count_str) if count_str else 0

    async def get_stats(self) -> dict:
        """Get current bucket statistics."""
        tokens_str = await self.redis_client.get(self.tokens_key)
        timestamp_str = await self.redis_client.get(self.timestamp_key)
        concurrent_count = await self._get_concurrent_count()

        tokens = float(tokens_str) if tokens_str else self.max_tokens
        last_refill = float(timestamp_str) if timestamp_str else time.time()

        return {
            "domain": self.domain,
            "tokens": tokens,
            "max_tokens": self.max_tokens,
            "refill_rate": self.refill_rate,
            "concurrent_count": concurrent_count,
            "concurrent_limit": self.concurrent_limit,
            "last_refill": last_refill,
        }


def extract_domain(url: str) -> str:
    """Extract domain from URL."""
    parsed = urlparse(url)
    return parsed.netloc or parsed.path
