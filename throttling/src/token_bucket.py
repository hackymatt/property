"""In-memory token bucket rate limiter."""

import asyncio
import time


class RateLimiter:
    """
    Token bucket rate limiter using asyncio.

    Tokens refill at `rate` per second up to `burst` capacity.
    `acquire()` sleeps exactly long enough for a token to become available
    — no polling, no Redis.
    """

    def __init__(self, rate: float, burst: int):
        self.rate = rate
        self.burst = burst
        self._tokens = float(burst)
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_refill
            self._tokens = min(float(self.burst), self._tokens + elapsed * self.rate)
            self._last_refill = now

            if self._tokens >= 1.0:
                self._tokens -= 1.0
                return

            # Calculate exact wait so the token will be ready
            wait = (1.0 - self._tokens) / self.rate
            self._tokens = 0.0
            # Advance virtual clock so the next caller accounts for this wait
            self._last_refill = now + wait

        await asyncio.sleep(wait)
