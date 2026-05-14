"""
Throttle Helper for Scrapers
Provides easy-to-use utilities for interacting with the throttling service via RabbitMQ.
"""

import asyncio
import json
import uuid
import time
from contextlib import asynccontextmanager
from typing import Optional

from shared.rabbitmq import RabbitMQClient
from shared.logger import get_logger

logger = get_logger("throttle_helper")


class ThrottleHelper:
    """
    Helper class for using the throttling service from scrapers.
    Handles RabbitMQ communication with the throttling service.
    """

    def __init__(
        self, rabbitmq_client: RabbitMQClient, throttle_queue: str = "throttle_requests"
    ):
        """
        Initialize throttle helper.

        Args:
            rabbitmq_client: Connected RabbitMQ client instance
            throttle_queue: Queue name for throttling service
        """
        self.rabbitmq = rabbitmq_client
        self.throttle_queue = throttle_queue
        self._response_queue = f"throttle_response_{uuid.uuid4().hex[:8]}"
        self._pending_requests = {}
        self._consumer_started = False
        # Metrics tracking
        self._metrics = {
            "acquire_attempts": 0,
            "acquire_success": 0,
            "acquire_failures": 0,
            "total_wait_time": 0.0,
            "per_domain": {},
        }

    async def start(self):
        """Start consuming responses from the response queue."""
        if not self._consumer_started:
            await self.rabbitmq.consume(
                queue=self._response_queue,
                callback=self._handle_response,
                auto_delete=True,
                exclusive=True,
                blocking=False,
            )
            self._consumer_started = True
            logger.info(
                f"Throttle helper started, consuming from response queue: {self._response_queue}"
            )

    async def _handle_response(self, message):
        """Handle response messages from throttling service."""
        try:
            body = message.body.decode()
            data = json.loads(body)

            logger.info(f"Received throttle response: {data}")

            # Find the pending request this response is for
            request_id = data.get("request_id")
            if request_id and request_id in self._pending_requests:
                future = self._pending_requests.pop(request_id)
                future.set_result(data)
                logger.info(f"Resolved future for request_id={request_id}")
            else:
                logger.warning(f"No pending request found for request_id={request_id}")

            await message.ack()

        except Exception as e:
            logger.error(f"Error handling response: {e}", exc_info=True)
            await message.reject(requeue=False)

    async def acquire(
        self, domain: str, timeout: float = None, max_retries: int = 3
    ) -> bool:
        """
        Acquire a token to make a request to the given domain with exponential backoff retry.

        Args:
            domain: Domain name for rate limiting
            timeout: Maximum time to wait for a token (seconds). None = wait indefinitely
            max_retries: Maximum number of retry attempts

        Returns:
            True if token acquired, False otherwise
        """
        if not self._consumer_started:
            await self.start()

        self._metrics["acquire_attempts"] += 1
        if domain not in self._metrics["per_domain"]:
            self._metrics["per_domain"][domain] = {
                "attempts": 0,
                "success": 0,
                "failures": 0,
                "wait_time": 0.0,
            }
        self._metrics["per_domain"][domain]["attempts"] += 1

        request_start = time.time()
        retry_count = 0

        while retry_count < max_retries:
            request_id = str(uuid.uuid4())
            future = asyncio.Future()
            self._pending_requests[request_id] = future

            try:
                # Send acquire request
                await self.rabbitmq.publish(
                    queue=self.throttle_queue,
                    message={
                        "action": "acquire",
                        "domain": domain,
                        "timeout": (
                            timeout if timeout is not None else 0
                        ),  # 0 means no timeout in throttle service
                        "reply_to": self._response_queue,
                        "request_id": request_id,
                    },
                    durable=True,
                )

                # Wait for response with timeout (or indefinitely if None)
                # Add 10 seconds buffer for network/processing time
                response_timeout = (timeout + 10) if timeout is not None else None
                if response_timeout is not None:
                    response = await asyncio.wait_for(future, timeout=response_timeout)
                else:
                    response = await future

                success = response.get("success", False)
                wait_time = time.time() - request_start

                if success:
                    self._metrics["acquire_success"] += 1
                    self._metrics["total_wait_time"] += wait_time
                    self._metrics["per_domain"][domain]["success"] += 1
                    self._metrics["per_domain"][domain]["wait_time"] += wait_time
                    logger.debug(
                        f"Token acquired for domain={domain} (wait_time={wait_time:.2f}s)"
                    )
                    return True
                else:
                    # Temporary failure, retry with exponential backoff
                    retry_count += 1
                    if retry_count < max_retries:
                        backoff_time = min(2**retry_count, 10)  # Cap at 10 seconds
                        logger.warning(
                            f"Failed to acquire token for domain={domain}: {response.get('error')}. "
                            f"Retrying ({retry_count}/{max_retries}) after {backoff_time}s"
                        )
                        await asyncio.sleep(backoff_time)
                    else:
                        logger.error(
                            f"Failed to acquire token for domain={domain} after {max_retries} retries"
                        )
                        self._metrics["acquire_failures"] += 1
                        self._metrics["per_domain"][domain]["failures"] += 1
                        return False

            except asyncio.TimeoutError:
                retry_count += 1
                if retry_count < max_retries:
                    backoff_time = min(2**retry_count, 10)
                    logger.warning(
                        f"Timeout waiting for throttle response for domain={domain}. "
                        f"Retrying ({retry_count}/{max_retries}) after {backoff_time}s"
                    )
                    self._pending_requests.pop(request_id, None)
                    await asyncio.sleep(backoff_time)
                else:
                    logger.error(
                        f"Timeout waiting for throttle response for domain={domain} after {max_retries} retries"
                    )
                    self._pending_requests.pop(request_id, None)
                    self._metrics["acquire_failures"] += 1
                    self._metrics["per_domain"][domain]["failures"] += 1
                    return False
            except Exception as e:
                retry_count += 1
                if retry_count < max_retries:
                    backoff_time = min(2**retry_count, 10)
                    logger.warning(
                        f"Error acquiring token for domain={domain}: {e}. "
                        f"Retrying ({retry_count}/{max_retries}) after {backoff_time}s"
                    )
                    self._pending_requests.pop(request_id, None)
                    await asyncio.sleep(backoff_time)
                else:
                    logger.error(
                        f"Error acquiring token for domain={domain} after {max_retries} retries: {e}",
                        exc_info=True,
                    )
                    self._pending_requests.pop(request_id, None)
                    self._metrics["acquire_failures"] += 1
                    self._metrics["per_domain"][domain]["failures"] += 1
                    return False

        return False

    async def pause(self, domain: str, duration: int) -> None:
        """Signal the throttle service to pause a domain for `duration` seconds."""
        try:
            await self.rabbitmq.publish(
                queue=self.throttle_queue,
                message={"action": "pause", "domain": domain, "duration": duration},
                durable=True,
            )
            logger.info(f"Pause signal sent for domain={domain} duration={duration}s")
        except Exception as e:
            logger.error(f"Error sending pause for domain={domain}: {e}", exc_info=True)

    async def release(self, domain: str) -> bool:
        """
        Release a token after completing a request.
        Fire-and-forget - doesn't wait for response.

        Args:
            domain: Domain name

        Returns:
            True if message sent, False on error
        """
        try:
            await self.rabbitmq.publish(
                queue=self.throttle_queue,
                message={
                    "action": "release",
                    "domain": domain,
                },
                durable=True,
            )
            logger.info(f"Token released for domain={domain}")
            return True

        except Exception as e:
            logger.error(
                f"Error releasing token for domain={domain}: {e}", exc_info=True
            )
            return False

    @asynccontextmanager
    async def throttled_request(
        self, domain: str, timeout: float = None, max_retries: int = 3
    ):
        """
        Context manager for throttled requests.
        Automatically acquires and releases tokens.

        Usage:
            async with throttle_helper.throttled_request(domain) as acquired:
                if acquired:
                    # Make your scraping request here
                    response = await scrape(url)

        Args:
            domain: Domain name for rate limiting
            timeout: Maximum time to wait for a token (seconds). None = wait indefinitely
            max_retries: Maximum number of retry attempts

        Yields:
            bool: True if token was acquired, False otherwise
        """
        acquired = await self.acquire(domain, timeout, max_retries)
        try:
            yield acquired
        finally:
            if acquired:
                await self.release(domain)

    def get_metrics(self) -> dict:
        """Get throttling metrics for monitoring."""
        return {
            "total_acquire_attempts": self._metrics["acquire_attempts"],
            "total_acquire_success": self._metrics["acquire_success"],
            "total_acquire_failures": self._metrics["acquire_failures"],
            "success_rate": (
                self._metrics["acquire_success"]
                / self._metrics["acquire_attempts"]
                * 100
                if self._metrics["acquire_attempts"] > 0
                else 0
            ),
            "average_wait_time": (
                self._metrics["total_wait_time"] / self._metrics["acquire_success"]
                if self._metrics["acquire_success"] > 0
                else 0
            ),
            "per_domain": self._metrics["per_domain"],
        }
