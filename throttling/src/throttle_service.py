"""
Main Throttling Service
RabbitMQ-based service that manages rate limiting for scraping requests.
"""

import asyncio
import json
from typing import Dict

from src.logger import logger
from src.domain_config import DomainConfig
from src.token_bucket import TokenBucket
from config import (
    DATABASE_URL,
    REDIS_HOST,
    REDIS_PORT,
    REDIS_DB,
    REDIS_PASSWORD,
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
from shared.redis_client import RedisClient
from shared.database import DatabaseManager

# Dead letter queue for failed requests (retry exhausted)
RABBITMQ_DLQ = "throttle_requests_dlq"


class ThrottleService:
    """RabbitMQ-based throttling service managing token buckets for all domains."""

    def __init__(self):
        self.db = DatabaseManager(database_url=DATABASE_URL, logger_name="throttling")
        self.redis_client = RedisClient(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            password=REDIS_PASSWORD,
        )
        self.rabbitmq = RabbitMQClient(
            host=RABBITMQ_HOST,
            port=RABBITMQ_PORT,
            username=RABBITMQ_USER,
            password=RABBITMQ_PASSWORD,
            virtual_host=RABBITMQ_VHOST,
        )
        self.domain_config: DomainConfig = None
        self.token_buckets: Dict[str, TokenBucket] = {}
        self._buckets_lock = asyncio.Lock()
        self.running = False

    async def startup(self):
        """Initialize all connections."""
        logger.info("Starting throttling service...")

        # Initialize database
        await self.db.init(retries=STARTUP_RETRIES, delay=STARTUP_RETRY_DELAY)
        logger.info("Database initialized")

        # Initialize Redis
        await self.redis_client.connect_with_retry(
            retries=STARTUP_RETRIES,
            delay=STARTUP_RETRY_DELAY,
            logger=logger,
        )
        logger.info("Redis connected")

        # Initialize RabbitMQ
        await self.rabbitmq.connect_with_retry(
            retries=STARTUP_RETRIES,
            delay=STARTUP_RETRY_DELAY,
            logger=logger,
        )
        logger.info("RabbitMQ connected")

        # Initialize domain config manager
        self.domain_config = DomainConfig(self.db.get_session)
        await self.domain_config.start()

        logger.info("Throttling service initialized successfully")

    async def shutdown(self):
        """Cleanup connections on shutdown."""
        logger.info("Shutting down throttling service...")

        self.running = False

        if self.domain_config:
            await self.domain_config.stop()

        if self.redis_client:
            await self.redis_client.close()

        logger.info("Throttling service shut down")

    async def get_or_create_bucket(self, domain: str) -> TokenBucket:
        """Get existing token bucket or create a new one for the domain."""
        async with self._buckets_lock:
            if domain in self.token_buckets:
                return self.token_buckets[domain]

            # Get config for this domain
            config = await self.domain_config.get_config(domain)

            # Create new bucket with burst_capacity from config
            max_tokens = config.get("burst_capacity", 2)

            bucket = TokenBucket(
                redis_client=self.redis_client.get_client(),
                domain=domain,
                refill_rate=config["requests_per_second"],
                max_tokens=max_tokens,
                concurrent_limit=config["concurrent_requests"],
            )

            self.token_buckets[domain] = bucket
            logger.info(f"Created token bucket for domain: {domain}")

            return bucket

    async def handle_acquire_request(self, message_data: dict) -> dict:
        """
        Handle an acquire token request.

        Message format:
        {
            "action": "acquire",
            "domain": "example.com",
            "timeout": 60.0,
            "reply_to": "scraper_response_queue"
        }

        Returns response dict to send back.
        """
        try:
            domain = message_data.get("domain")
            timeout = message_data.get("timeout")
            # Convert timeout: None or 0 means no timeout
            if timeout == 0:
                timeout = None

            if not domain:
                return {
                    "success": False,
                    "error": "Domain is required",
                }

            bucket = await self.get_or_create_bucket(domain)

            # Try to acquire token
            logger.info(
                f"Attempting to acquire token for domain={domain} with timeout={timeout}"
            )
            success = await bucket.acquire(timeout=timeout)
            logger.info(
                f"Token acquisition result for domain={domain}: success={success}"
            )

            request_id = message_data.get("request_id")

            if success:
                return {
                    "success": True,
                    "message": "Token acquired",
                    "domain": domain,
                    "request_id": request_id,
                }
            else:
                return {
                    "success": False,
                    "error": "Timeout waiting for token",
                    "domain": domain,
                    "request_id": request_id,
                }

        except Exception as e:
            logger.error(f"Error handling acquire request: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
            }

    async def handle_release_request(self, message_data: dict) -> dict:
        """
        Handle a release token request.

        Message format:
        {
            "action": "release",
            "domain": "example.com",
            "reply_to": "scraper_response_queue"
        }

        Returns response dict to send back.
        """
        try:
            domain = message_data.get("domain")

            if not domain:
                return {
                    "success": False,
                    "error": "Domain is required",
                }

            bucket = await self.get_or_create_bucket(domain)

            await bucket.release()

            return {
                "success": True,
                "message": "Token released",
                "domain": domain,
            }

        except Exception as e:
            logger.error(f"Error handling release request: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
            }

    async def process_message(self, message):
        """Process incoming RabbitMQ message with dead letter queue handling."""
        retry_count = (
            message.headers.get("x-death", [{}])[0].get("count", 0)
            if hasattr(message, "headers")
            else 0
        )

        try:
            body = message.body.decode()
            data = json.loads(body)

            action = data.get("action")
            reply_to = data.get("reply_to")
            domain = data.get("domain")

            # Get domain-specific configuration for max_retries
            config = await self.domain_config.get_config(domain) if domain else {}
            max_retries = config.get("max_retries", 3)

            logger.info(
                f"Processing {action} request for domain={domain} (retry_count={retry_count})"
            )

            # Handle the request
            if action == "acquire":
                response = await self.handle_acquire_request(data)
            elif action == "release":
                response = await self.handle_release_request(data)
            else:
                response = {
                    "success": False,
                    "error": f"Unknown action: {action}",
                }

            # Send response back if reply_to is specified
            logger.info(f"Response generated: {response}, reply_to={reply_to}")
            if reply_to:
                logger.info(
                    f"Sending response to queue: {reply_to}, success={response.get('success')}"
                )
                await self.rabbitmq.publish(
                    reply_to, response, durable=False, declare_queue=False
                )
            else:
                logger.warning("No reply_to specified, not sending response")

            await message.ack()

        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode message: {e}")
            await message.reject(requeue=False)
        except Exception as e:
            logger.error(
                f"Error processing message (retry_count={retry_count}): {e}",
                exc_info=True,
            )

            # Implement dead letter queue logic
            if retry_count < max_retries:
                # Get retry_delay from domain config
                retry_delay = config.get("retry_delay", 5.0)
                logger.warning(
                    f"Requeuing message for retry ({retry_count + 1}/{max_retries}) after {retry_delay}s delay"
                )
                # Wait before requeuing to implement retry delay
                await asyncio.sleep(retry_delay)
                await message.reject(requeue=True)
            else:
                # Send to DLQ after max retries
                try:
                    dlq_message = {
                        "original_message": (
                            json.loads(message.body.decode())
                            if isinstance(message.body, bytes)
                            else message.body
                        ),
                        "error": str(e),
                        "retry_count": retry_count,
                        "timestamp": asyncio.get_event_loop().time(),
                    }
                    await self.rabbitmq.publish(RABBITMQ_DLQ, dlq_message, durable=True)
                    logger.error(
                        f"Message sent to DLQ after {max_retries} retries: {dlq_message}"
                    )
                except Exception as dlq_error:
                    logger.critical(
                        f"Failed to send message to DLQ: {dlq_error}. Original error: {e}",
                        exc_info=True,
                    )

                await message.reject(requeue=False)

    async def run(self):
        """Run the throttling service - consume messages from RabbitMQ."""
        await self.startup()

        self.running = True

        try:
            logger.info(f"Starting to consume from queue: {RABBITMQ_THROTTLE_QUEUE}")

            # Start consuming DLQ messages in background (non-blocking)
            asyncio.create_task(self._consume_dlq())

            # Main queue consumer
            await self.rabbitmq.consume(
                queue=RABBITMQ_THROTTLE_QUEUE,
                callback=self.process_message,
                prefetch_count=100,  # Process up to 100 messages concurrently
            )
        except asyncio.CancelledError:
            logger.info("Received shutdown signal")
        except Exception as e:
            logger.critical(f"Fatal error in throttling service: {e}", exc_info=True)
            raise
        finally:
            await self.shutdown()

    async def _consume_dlq(self):
        """Consume and log messages from dead letter queue."""
        try:

            async def dlq_handler(message):
                try:
                    body = message.body.decode()
                    data = json.loads(body)
                    logger.warning(
                        f"DLQ Message - domain={data.get('original_message', {}).get('domain')}, "
                        f"error={data.get('error')}, retry_count={data.get('retry_count')}"
                    )
                    await message.ack()
                except Exception as e:
                    logger.error(f"Error handling DLQ message: {e}", exc_info=True)
                    await message.reject(requeue=False)

            await self.rabbitmq.consume(
                queue=RABBITMQ_DLQ,
                callback=dlq_handler,
                prefetch_count=10,
            )
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in DLQ consumer: {e}", exc_info=True)
