"""
Throttling Service — dispatcher-based rate limiter.

Each domain gets one DomainThrottle that owns:
  - a RateLimiter  (token bucket, in-memory, no polling)
  - a Semaphore    (concurrent-request cap)
  - a Queue        (pending acquire requests, FIFO)
  - a dispatcher   (single background coroutine that grants tokens in order)

Incoming RabbitMQ messages are acked immediately so the channel stays clear.
Releases call semaphore.release() inline — they are never queued.
"""

import asyncio
import json
import time
from typing import Dict

from src.logger import logger
from src.domain_config import DomainConfig
from src.token_bucket import RateLimiter
from config import (
    DATABASE_URL,
    RABBITMQ_HOST,
    RABBITMQ_PORT,
    RABBITMQ_USER,
    RABBITMQ_PASSWORD,
    RABBITMQ_VHOST,
    RABBITMQ_THROTTLE_QUEUE,
    STARTUP_RETRIES,
    STARTUP_RETRY_DELAY,
)
from shared.rabbitmq import RabbitMQClient
from shared.database import DatabaseManager


class DomainThrottle:
    """Per-domain token dispatcher."""

    # If a granted slot isn't released within this many seconds, auto-release it
    SLOT_TIMEOUT = 120

    def __init__(self, domain: str, rate: float, burst: int, concurrent_limit: int, rabbitmq: RabbitMQClient):
        self.domain = domain
        self._rate_limiter = RateLimiter(rate, burst)
        self._concurrent_limit = concurrent_limit
        self._semaphore = asyncio.Semaphore(concurrent_limit)
        self._queue: asyncio.Queue = asyncio.Queue()
        self._rabbitmq = rabbitmq
        self._task: asyncio.Task = None
        self._paused_until: float = 0.0

    def start(self):
        self._task = asyncio.create_task(self._dispatcher())
        logger.info(f"Dispatcher started for domain={self.domain}")

    def stop(self):
        if self._task:
            self._task.cancel()

    async def enqueue(self, request_id: str, reply_to: str):
        await self._queue.put((request_id, reply_to))

    def release(self):
        try:
            self._semaphore.release()
            logger.debug(f"Concurrent slot released for domain={self.domain}")
        except ValueError:
            logger.warning(f"release() called with no active slot for domain={self.domain}")

    def pause(self, duration: int):
        self._paused_until = time.monotonic() + duration
        logger.warning(f"Domain {self.domain} paused for {duration}s (429 received)")

    async def _dispatcher(self):
        while True:
            try:
                request_id, reply_to = await self._queue.get()

                # Respect 429 pause before doing anything else
                remaining = self._paused_until - time.monotonic()
                if remaining > 0:
                    logger.info(f"Domain {self.domain} is paused, waiting {remaining:.1f}s")
                    await asyncio.sleep(remaining)

                # Wait for rate-limit token (precise sleep, no polling)
                await self._rate_limiter.acquire()

                # Wait for a concurrent slot — timeout guards against stale held slots
                # (e.g. scraper crashed before sending release)
                try:
                    await asyncio.wait_for(self._semaphore.acquire(), timeout=self.SLOT_TIMEOUT)
                except asyncio.TimeoutError:
                    logger.warning(
                        f"Semaphore timeout for domain={self.domain} — "
                        f"resetting to {self._concurrent_limit} (stale slot detected)"
                    )
                    self._semaphore = asyncio.Semaphore(self._concurrent_limit)
                    await self._semaphore.acquire()

                # Grant the token — fire-and-forget style (don't let send errors stall the queue)
                try:
                    await self._rabbitmq.publish(
                        reply_to,
                        {
                            "success": True,
                            "message": "Token acquired",
                            "domain": self.domain,
                            "request_id": request_id,
                        },
                        durable=False,
                        declare_queue=False,
                    )
                    logger.debug(f"Token granted domain={self.domain} request_id={request_id}")
                except Exception:
                    logger.exception(f"Failed to send token response for domain={self.domain}, releasing slot")
                    self._semaphore.release()

            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception(f"Unexpected error in dispatcher for domain={self.domain}")


class ThrottleService:
    def __init__(self):
        self.db = DatabaseManager(database_url=DATABASE_URL, logger_name="throttling")
        self.rabbitmq = RabbitMQClient(
            host=RABBITMQ_HOST,
            port=RABBITMQ_PORT,
            username=RABBITMQ_USER,
            password=RABBITMQ_PASSWORD,
            virtual_host=RABBITMQ_VHOST,
        )
        self.domain_config: DomainConfig = None
        self._throttles: Dict[str, DomainThrottle] = {}
        self._throttles_lock = asyncio.Lock()

    async def startup(self):
        logger.info("Starting throttling service...")

        await self.db.init(retries=STARTUP_RETRIES, delay=STARTUP_RETRY_DELAY)
        logger.info("Database initialized")

        await self.rabbitmq.connect_with_retry(
            retries=STARTUP_RETRIES,
            delay=STARTUP_RETRY_DELAY,
            logger=logger,
        )
        logger.info("RabbitMQ connected")

        self.domain_config = DomainConfig(self.db.get_session)
        await self.domain_config.start()
        logger.info("Throttling service ready")

    async def shutdown(self):
        logger.info("Shutting down throttling service...")
        async with self._throttles_lock:
            for throttle in self._throttles.values():
                throttle.stop()
        if self.domain_config:
            await self.domain_config.stop()
        logger.info("Throttling service shut down")

    async def _get_or_create_throttle(self, domain: str) -> DomainThrottle:
        async with self._throttles_lock:
            if domain in self._throttles:
                return self._throttles[domain]

            config = await self.domain_config.get_config(domain)
            throttle = DomainThrottle(
                domain=domain,
                rate=config["requests_per_second"],
                burst=config.get("burst_capacity", 2),
                concurrent_limit=config["concurrent_requests"],
                rabbitmq=self.rabbitmq,
            )
            throttle.start()
            self._throttles[domain] = throttle
            logger.info(
                f"Created throttle for domain={domain} "
                f"rate={config['requests_per_second']}/s burst={config.get('burst_capacity', 2)} "
                f"concurrent={config['concurrent_requests']}"
            )
            return throttle

    async def process_message(self, message):
        try:
            data = json.loads(message.body.decode())
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.error(f"Malformed message: {e}")
            await message.reject(requeue=False)
            return

        action = data.get("action")
        domain = data.get("domain")

        try:
            if action == "acquire":
                request_id = data.get("request_id")
                reply_to = data.get("reply_to")

                if not domain or not reply_to:
                    logger.warning(f"acquire missing domain or reply_to: {data}")
                    await message.reject(requeue=False)
                    return

                throttle = await self._get_or_create_throttle(domain)
                await throttle.enqueue(request_id, reply_to)
                await message.ack()
                logger.debug(f"Queued acquire domain={domain} request_id={request_id} queue_size={throttle._queue.qsize()}")

            elif action == "release":
                if domain and domain in self._throttles:
                    self._throttles[domain].release()
                await message.ack()

            elif action == "pause":
                duration = int(data.get("duration", 60))
                if domain:
                    throttle = await self._get_or_create_throttle(domain)
                    throttle.pause(duration)
                await message.ack()

            else:
                logger.warning(f"Unknown action: {action}")
                await message.reject(requeue=False)

        except Exception:
            logger.exception(f"Error processing {action} for domain={domain}")
            await message.reject(requeue=False)

    async def run(self):
        await self.startup()
        try:
            logger.info(f"Consuming from queue: {RABBITMQ_THROTTLE_QUEUE}")
            await self.rabbitmq.consume(
                queue=RABBITMQ_THROTTLE_QUEUE,
                callback=self.process_message,
                prefetch_count=200,
            )
        except asyncio.CancelledError:
            logger.info("Received shutdown signal")
        except Exception:
            logger.exception("Fatal error in throttling service")
            raise
        finally:
            await self.shutdown()
