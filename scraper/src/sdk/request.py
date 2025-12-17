import httpx
from src.logger import logger


class Request:
    def __init__(self, throttle_helper):
        self.throttle_helper = throttle_helper

    async def __aenter__(self):
        self.client = httpx.AsyncClient()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    async def request(self, method, url, *, domain, timeout=30, **kwargs):
        """
        Make an HTTP request with optional throttling and robust logging/timeouts.
        Args:
            method: HTTP method (GET, POST, etc.)
            url: URL to request
            domain: Domain for throttling (required if throttle_helper is set)
            timeout: Timeout for the HTTP request (seconds, default 30)
            **kwargs: Passed to httpx.AsyncClient.request
        Returns:
            httpx.Response
        """
        async with self.throttle_helper.throttled_request(domain) as acquired:
            if not acquired:
                logger.error(
                    f"Failed to acquire throttle token for domain {domain} (request to {url})"
                )
                raise RuntimeError(
                    f"Failed to acquire throttle token for domain {domain}"
                )
            logger.info(f"[Request] {method} {url} (domain={domain}) - START")
            try:
                response = await self.client.request(
                    method, url, timeout=timeout, **kwargs
                )
                logger.info(
                    f"[Request] {method} {url} (domain={domain}) - SUCCESS {response.status_code}"
                )
                return response
            except httpx.TimeoutException:
                logger.error(
                    f"[Request] {method} {url} (domain={domain}) - TIMEOUT after {timeout}s"
                )
                raise
            except Exception as e:
                logger.error(
                    f"[Request] {method} {url} (domain={domain}) - ERROR: {e}",
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
