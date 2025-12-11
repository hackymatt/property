import asyncio
import time
from urllib.parse import urlparse
from collections import defaultdict, deque


class DomainThrottle:
    def __init__(
        self, max_requests_per_second: float = 2.0, max_requests_per_24h: int = 10000
    ):
        self.max_requests_per_second = max_requests_per_second
        self.max_requests_per_24h = max_requests_per_24h
        self._locks = defaultdict(asyncio.Lock)
        self._request_history_24h = defaultdict(
            deque
        )  # Track requests in last 24h per domain
        self._request_history_1s = defaultdict(
            deque
        )  # Track requests in last 1 second per domain

    async def wait(self, url: str):
        """Wait if necessary before accessing the given URL's domain."""
        domain = self._extract_domain(url)

        async with self._locks[domain]:
            now = time.time()

            # Clean old requests from 24h history (older than 24h)
            cutoff_time_24h = now - 86400  # 24 hours in seconds
            history_24h = self._request_history_24h[domain]
            while history_24h and history_24h[0] < cutoff_time_24h:
                history_24h.popleft()

            # Check 24h limit
            if len(history_24h) >= self.max_requests_per_24h:
                oldest_request = history_24h[0]
                wait_time = (oldest_request + 86400) - now
                if wait_time > 0:
                    raise RuntimeError(
                        f"Domain {domain} has reached the 24h request limit ({self.max_requests_per_24h}). "
                        f"Wait {wait_time:.0f} seconds before retrying."
                    )

            # Clean old requests from 1s history (older than 1 second)
            cutoff_time_1s = now - 1.0
            history_1s = self._request_history_1s[domain]
            while history_1s and history_1s[0] < cutoff_time_1s:
                history_1s.popleft()

            # Check requests per second limit
            if len(history_1s) >= self.max_requests_per_second:
                oldest_request_1s = history_1s[0]
                wait_time = (oldest_request_1s + 1.0) - now
                if wait_time > 0:
                    await asyncio.sleep(wait_time)
                    now = time.time()
                    # Clean again after sleeping
                    cutoff_time_1s = now - 1.0
                    while history_1s and history_1s[0] < cutoff_time_1s:
                        history_1s.popleft()

            # Record this request in both histories
            self._request_history_24h[domain].append(now)
            self._request_history_1s[domain].append(now)

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        parsed = urlparse(url)
        return parsed.netloc or parsed.path
