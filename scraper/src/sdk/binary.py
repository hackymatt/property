"""Throttled HTTP helpers for binary payloads.

src/sdk/request.py::Request always reads the body as text, which corrupts
(or chokes on) binary content. These helpers go through the same
`throttle_helper.throttled_request()` primitive, so global per-domain rate
limiting still applies — no caller may bypass it.
"""

import asyncio
import logging
from pathlib import Path

import aiohttp

logger = logging.getLogger(__name__)


async def read_exactly(stream, num_bytes: int) -> bytes:
    """Read exactly num_bytes (or fewer only if the body ends first).

    A single `stream.read(n)` returns however much happens to be buffered —
    often far less than n, and a different amount each call. Anything that
    hashes the result needs this to stay deterministic.
    """
    buffer = bytearray()
    while len(buffer) < num_bytes:
        chunk = await stream.read(num_bytes - len(buffer))
        if not chunk:
            break
        buffer.extend(chunk)
    return bytes(buffer)


async def throttled_head(throttle_helper, domain: str, url: str, timeout: int = 15) -> dict | None:
    async with throttle_helper.throttled_request(domain) as acquired:
        if not acquired:
            logger.warning("[binary] Failed to acquire throttle token for HEAD %s", url)
            return None
        try:
            async with aiohttp.ClientSession() as session:
                async with session.head(url, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                    if resp.status != 200:
                        return None
                    return {"status": resp.status, "headers": dict(resp.headers)}
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            logger.warning("[binary] HEAD failed for %s: %s", url, e)
            return None


async def throttled_get_bytes(
    throttle_helper,
    domain: str,
    url: str,
    headers: dict | None = None,
    timeout: int = 30,
    max_bytes: int | None = None,
) -> bytes | None:
    """`max_bytes` caps how much of the body is read. Essential when a server
    ignores a Range request and answers 200 with the whole file — reading it
    all would simply time out."""
    async with throttle_helper.throttled_request(domain) as acquired:
        if not acquired:
            logger.warning("[binary] Failed to acquire throttle token for GET %s", url)
            return None
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                    if resp.status not in (200, 206):
                        logger.warning("[binary] status=%s for %s", resp.status, url)
                        return None
                    if max_bytes is None:
                        return await resp.read()
                    return await read_exactly(resp.content, max_bytes)
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            logger.warning("[binary] GET failed for %s: %s", url, e)
            return None


async def throttled_download_to_file(
    throttle_helper,
    domain: str,
    url: str,
    dest_path: Path,
    chunk_size: int = 1024 * 1024,
    sock_read_timeout: int = 120,
) -> bool:
    """Deliberately NO total timeout: a slow-but-progressing download must
    not be killed for taking a while. `sock_read` still fails fast when the
    connection actually stalls."""
    timeout = aiohttp.ClientTimeout(total=None, sock_connect=30, sock_read=sock_read_timeout)

    async with throttle_helper.throttled_request(domain) as acquired:
        if not acquired:
            logger.warning("[binary] Failed to acquire throttle token for download %s", url)
            return False
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=timeout) as resp:
                    if resp.status != 200:
                        logger.warning("[binary] status=%s downloading %s", resp.status, url)
                        return False
                    expected = resp.headers.get("Content-Length")
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    written = 0
                    with open(dest_path, "wb") as f:
                        async for chunk in resp.content.iter_chunked(chunk_size):
                            f.write(chunk)
                            written += len(chunk)
            logger.info("[binary] Downloaded %s (%d bytes) -> %s", url, written, dest_path)

            # A truncated file can still pass a structural check often enough
            # to be dangerous, so verify against Content-Length when given.
            if expected is not None and written != int(expected):
                logger.warning(
                    "[binary] Truncated download for %s: got %d bytes, expected %s", url, written, expected,
                )
                dest_path.unlink(missing_ok=True)
                return False
            return True
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            logger.warning("[binary] Download failed for %s: %s", url, e)
            dest_path.unlink(missing_ok=True)
            return False
