import asyncio
import aiohttp
from src.logger import logger


class RetriableError(Exception):
    def __init__(self, message: str, retry_after: int):
        super().__init__(message)
        self.retry_after = retry_after


class TooManyRequestsError(RetriableError):
    def __init__(self, url: str, retry_after: int):
        super().__init__(f"429 Too Many Requests for {url}, retry after {retry_after}s", retry_after)


class ForbiddenError(RetriableError):
    def __init__(self, url: str, retry_after: int):
        super().__init__(f"403 Forbidden for {url}, retry after {retry_after}s", retry_after)


class NetworkError(RetriableError):
    def __init__(self, url: str, reason: str, retry_after: int = 30):
        super().__init__(f"Network error for {url}: {reason}", retry_after)


class Request:
    def __init__(self, throttle_helper):
        self.throttle_helper = throttle_helper
        self.client: aiohttp.ClientSession | None = None

    async def __aenter__(self):
        timeout = aiohttp.ClientTimeout(total=30)
        self.client = aiohttp.ClientSession(timeout=timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.close()

    async def request(self, method, url, *, domain, timeout=30, **kwargs):
        async with self.throttle_helper.throttled_request(domain) as acquired:
            if not acquired:
                raise RuntimeError(f"Failed to acquire throttle token for {domain}")

            try:
                timeout_obj = aiohttp.ClientTimeout(total=timeout)

                async with self.client.request(
                    method,
                    url,
                    timeout=timeout_obj,
                    **kwargs,
                ) as resp:
                    text = await resp.text()

                    if resp.status == 429:
                        retry_after = int(resp.headers.get("Retry-After", 60))
                        logger.warning("[Request] 429 on %s (domain=%s), pausing %ss", url, domain, retry_after)
                        await self.throttle_helper.pause(domain, retry_after)
                        raise TooManyRequestsError(url, retry_after)

                    if resp.status == 403:
                        retry_after = int(resp.headers.get("Retry-After", 120))
                        logger.warning("[Request] 403 on %s (domain=%s), pausing %ss", url, domain, retry_after)
                        await self.throttle_helper.pause(domain, retry_after)
                        raise ForbiddenError(url, retry_after)

                    return {
                        "status": resp.status,
                        "headers": dict(resp.headers),
                        "text": text,
                        "url": str(resp.url),
                    }

            except asyncio.TimeoutError:
                logger.warning("[Request] %s %s (domain=%s) - TIMEOUT, will retry", method, url, domain)
                raise NetworkError(url, "timeout")

            except aiohttp.ClientError as e:
                logger.warning("[Request] %s %s (domain=%s) - CLIENT ERROR: %s, will retry", method, url, domain, e)
                raise NetworkError(url, str(e))

    async def get(self, url, *, domain, **kwargs):
        return await self.request("GET", url, domain=domain, **kwargs)

    async def post(self, url, *, domain, **kwargs):
        return await self.request("POST", url, domain=domain, **kwargs)

    async def put(self, url, *, domain, **kwargs):
        return await self.request("PUT", url, domain=domain, **kwargs)

    async def delete(self, url, *, domain, **kwargs):
        return await self.request("DELETE", url, domain=domain, **kwargs)
