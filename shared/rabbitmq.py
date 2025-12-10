"""Lightweight RabbitMQ helper for publishing and consuming messages."""

from typing import Callable, Optional
import json
import pika


class RabbitMQClient:
    """
    Minimal RabbitMQ client using pika.BlockingConnection.

    Usage:
        client = RabbitMQClient(host, port, username, password)
        client.connect()
        client.publish(queue="jobs", message={"id": 1})
        client.consume(queue="jobs", handler=handle_func)
    """

    def __init__(
        self,
        host: str,
        port: int = 5672,
        username: Optional[str] = None,
        password: Optional[str] = None,
        virtual_host: str = "/",
        heartbeat: int = 600,
        blocked_connection_timeout: int = 300,
    ):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.virtual_host = virtual_host
        self.heartbeat = heartbeat
        self.blocked_connection_timeout = blocked_connection_timeout
        self._connection: Optional[pika.BlockingConnection] = None
        self._channel: Optional[pika.adapters.blocking_connection.BlockingChannel] = None

    def connect(self):
        """Establish blocking connection and channel."""
        credentials = None
        if self.username and self.password:
            credentials = pika.PlainCredentials(self.username, self.password)

        params = pika.ConnectionParameters(
            host=self.host,
            port=self.port,
            virtual_host=self.virtual_host,
            heartbeat=self.heartbeat,
            blocked_connection_timeout=self.blocked_connection_timeout,
            credentials=credentials,
        )
        self._connection = pika.BlockingConnection(params)
        self._channel = self._connection.channel()

    def _ensure_channel(self):
        if not self._channel or self._channel.is_closed:
            raise RuntimeError("RabbitMQ channel is not open. Call connect() first.")

    def publish(self, queue: str, message, routing_key: Optional[str] = None, durable: bool = True):
        """
        Publish a message to a queue. Message is JSON-serialized.
        """
        self._ensure_channel()
        self._channel.queue_declare(queue=queue, durable=durable)
        body = json.dumps(message)
        self._channel.basic_publish(
            exchange="",
            routing_key=routing_key or queue,
            body=body,
            properties=pika.BasicProperties(delivery_mode=2 if durable else 1),
        )

    def consume(self, queue: str, handler: Callable[[dict], None], auto_ack: bool = False, durable: bool = True):
        """
        Consume messages from a queue and pass decoded JSON to handler.
        """
        self._ensure_channel()
        self._channel.queue_declare(queue=queue, durable=durable)

        def _callback(ch, method, properties, body):
            payload = json.loads(body)
            handler(payload)
            if not auto_ack:
                ch.basic_ack(delivery_tag=method.delivery_tag)

        self._channel.basic_qos(prefetch_count=1)
        self._channel.basic_consume(queue=queue, on_message_callback=_callback, auto_ack=auto_ack)
        self._channel.start_consuming()

    def close(self):
        """Close channel and connection if open."""
        if self._channel and not self._channel.is_closed:
            self._channel.close()
        if self._connection and not self._connection.is_closed:
            self._connection.close()