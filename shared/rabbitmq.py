"""Async RabbitMQ helper using aio-pika."""

import asyncio
import json
from typing import Callable, Optional, Awaitable

import aio_pika


class RabbitMQClient:
    def __init__(
        self,
        host: str,
        port: int = 5672,
        username: Optional[str] = None,
        password: Optional[str] = None,
        virtual_host: str = "/",
    ):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.virtual_host = virtual_host
        self._connection: Optional[aio_pika.RobustConnection] = None
        self._channel: Optional[aio_pika.abc.AbstractChannel] = None

    async def connect(self):
        self._connection = await aio_pika.connect_robust(
            host=self.host,
            port=self.port,
            login=self.username,
            password=self.password,
            virtualhost=self.virtual_host,
        )
        self._channel = await self._connection.channel()

    async def connect_with_retry(self, retries: int, delay: int, logger=None):
        for attempt in range(1, retries + 1):
            try:
                await self.connect()
                if logger:
                    logger.info("Connected to RabbitMQ")
                return
            except Exception as exc:
                if attempt == retries:
                    if logger:
                        logger.error(
                            f"RabbitMQ connection failed after {attempt} attempt(s): {exc} "
                            f"[host={self.host} user={self.username}]"
                        )
                    raise
                if logger:
                    logger.warning(
                        f"RabbitMQ connection failed (attempt {attempt}/{retries}): {exc}. "
                        f"Retrying in {delay}s... [host={self.host} user={self.username}]"
                    )
                await asyncio.sleep(delay)

    async def publish(
        self, queue: str, message, durable: bool = True, declare_queue: bool = True
    ):
        if not self._channel:
            raise RuntimeError("RabbitMQ channel is not open. Call connect() first.")

        if declare_queue:
            q = await self._channel.declare_queue(queue, durable=durable)
            routing_key = q.name
        else:
            routing_key = queue

        body = json.dumps(message).encode()
        await self._channel.default_exchange.publish(
            aio_pika.Message(
                body=body,
                delivery_mode=(
                    aio_pika.DeliveryMode.PERSISTENT
                    if durable
                    else aio_pika.DeliveryMode.NOT_PERSISTENT
                ),
            ),
            routing_key=routing_key,
        )

    async def publish_to_exchange(
        self,
        exchange: str,
        routing_key: str,
        message,
        exchange_type: aio_pika.ExchangeType = aio_pika.ExchangeType.TOPIC,
        durable: bool = True,
    ):
        """Publish message to an exchange for fanout/topic routing"""
        if not self._channel:
            raise RuntimeError("RabbitMQ channel is not open. Call connect() first.")

        ex = await self._channel.declare_exchange(
            exchange, exchange_type, durable=durable
        )
        body = json.dumps(message).encode()
        await ex.publish(
            aio_pika.Message(
                body=body,
                delivery_mode=(
                    aio_pika.DeliveryMode.PERSISTENT
                    if durable
                    else aio_pika.DeliveryMode.NOT_PERSISTENT
                ),
            ),
            routing_key=routing_key,
        )

    async def bind_queue_to_exchange(
        self,
        queue: str,
        exchange: str,
        routing_key: str,
        exchange_type: aio_pika.ExchangeType = aio_pika.ExchangeType.TOPIC,
        durable: bool = True,
    ):
        """Bind a queue to an exchange with a routing key"""
        if not self._channel:
            raise RuntimeError("RabbitMQ channel is not open. Call connect() first.")

        ex = await self._channel.declare_exchange(
            exchange, exchange_type, durable=durable
        )
        q = await self._channel.declare_queue(queue, durable=durable)
        await q.bind(ex, routing_key=routing_key)

    async def consume_forever(
        self,
        queue: str,
        handler: Callable[[dict, str], Awaitable[None]],
        durable: bool = True,
    ):
        if not self._channel:
            raise RuntimeError("RabbitMQ channel is not open. Call connect() first.")
        q = await self._channel.declare_queue(queue, durable=durable)

        async def _callback(message: aio_pika.IncomingMessage):
            try:
                payload = json.loads(message.body.decode())
                routing_key = message.routing_key or ""
                await handler(payload, routing_key)
                await message.ack()
            except Exception:
                # requeue=False: send to DLQ (if configured) rather than looping forever
                await message.nack(requeue=False)

        await q.consume(_callback)
        await asyncio.Future()  # run forever

    async def consume(
        self,
        queue: str,
        callback: Callable,
        prefetch_count: int = 1,
        durable: bool = True,
        auto_delete: bool = False,
        exclusive: bool = False,
        blocking: bool = True,
    ):
        """Consume messages from a queue with prefetch control."""
        if not self._channel:
            raise RuntimeError("RabbitMQ channel is not open. Call connect() first.")

        await self._channel.set_qos(prefetch_count=prefetch_count)
        q = await self._channel.declare_queue(
            queue, durable=durable, auto_delete=auto_delete, exclusive=exclusive
        )

        async def _wrapper(message: aio_pika.IncomingMessage):
            await callback(message)

        await q.consume(_wrapper)
        if blocking:
            await asyncio.Future()  # run forever

    async def close(self):
        if self._channel and not self._channel.is_closed:
            await self._channel.close()
        if self._connection and not self._connection.is_closed:
            await self._connection.close()
