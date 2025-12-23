import asyncio
import aiohttp
from src.logger import logger


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

                    return {
                        "status": resp.status,
                        "headers": dict(resp.headers),
                        "text": text,
                        "url": str(resp.url),
                    }

            except asyncio.TimeoutError:
                logger.error(f"[Request] {method} {url} (domain={domain}) - TIMEOUT")
                raise

            except aiohttp.ClientError as e:
                logger.error(
                    f"[Request] {method} {url} (domain={domain}) - CLIENT ERROR: {e}",
                    exc_info=True,
                )
                raise

    async def get(self, url, *, domain, **kwargs):
        return await self.request("GET", url, domain=domain, **kwargs)

    async def post(self, url, *, domain, **kwargs):
        return await self.request("POST", url, domain=domain, **kwargs)

    async def put(self, url, *, domain, **kwargs):
        return await self.request("PUT", url, domain=domain, **kwargs)

    async def delete(self, url, *, domain, **kwargs):
        return await self.request("DELETE", url, domain=domain, **kwargs)
