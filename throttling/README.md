# Throttling Service

A distributed rate-limiting service for web scraping that implements best practices to avoid being blocked. Uses RabbitMQ for message-based communication and Redis for distributed state.

## Features

- **Token Bucket Algorithm**: More lenient than fixed-window rate limiting, allows burst traffic while maintaining average rates
- **Per-Domain Configuration**: Each domain has its own rate limits loaded from the database
- **Distributed State**: Uses Redis for shared state across multiple service instances
- **Concurrent Request Limiting**: Controls the number of simultaneous requests per domain
- **Dynamic Configuration**: Automatically refreshes domain configs from the database
- **RabbitMQ Integration**: Message-based architecture for async communication

## Architecture

### Token Bucket Algorithm

The service uses the token bucket algorithm which:

- Adds tokens to a bucket at a constant rate (refill_rate)
- Has a maximum bucket capacity (allows burst traffic)
- Consumes one token per request
- Requests wait if no tokens are available

This is more sophisticated than simple rate limiting and mimics human-like request patterns better.

### Best Practices Implemented

1. **Rate Limiting**: Configurable requests per second per domain
2. **Concurrency Control**: Limits simultaneous connections to avoid overwhelming targets
3. **Distributed Coordination**: Redis ensures rate limits work across multiple scraper instances
4. **Burst Capacity**: Token bucket allows occasional bursts while maintaining average rate
5. **Per-Domain Config**: Different sites have different tolerances, configured in database
6. **Async Message Processing**: Non-blocking RabbitMQ-based communication

## Configuration

Domain configurations are stored in the `domain_domain` table with these fields:

- `requests_per_second`: Average rate (tokens added per second)
- `concurrent_requests`: Maximum simultaneous requests
- `delay_between_requests`: Minimum delay between requests
- `timeout`: Request timeout in seconds
- `max_retries`: Retry attempts for failed requests
- `retry_delay`: Delay before retrying

## RabbitMQ Messages

### Acquire Token Request

Send to queue: `throttle_requests`

```json
{
  "action": "acquire",
  "url": "https://example.com/page",
  "timeout": 60.0,
  "reply_to": "scraper_response_queue"
}
```

**Response:**

```json
{
  "success": true,
  "message": "Token acquired",
  "domain": "example.com"
}
```

Or on timeout:

```json
{
  "success": false,
  "error": "Timeout waiting for token",
  "domain": "example.com"
}
```

### Release Token Request

Send to queue: `throttle_requests`

```json
{
  "action": "release",
  "url": "https://example.com/page",
  "reply_to": "scraper_response_queue"
}
```

**Response:**

```json
{
  "success": true,
  "message": "Token released",
  "domain": "example.com"
}
```

## Usage Example

```python
from shared.rabbitmq import RabbitMQClient

rabbitmq = RabbitMQClient(...)
await rabbitmq.connect()

# Acquire token
await rabbitmq.publish(
    queue="throttle_requests",
    message={
        "action": "acquire",
        "url": "https://example.com/page",
        "timeout": 60.0,
        "reply_to": "my_response_queue"
    }
)

# Wait for response
# ... consume from my_response_queue ...

# After scraping, release token
await rabbitmq.publish(
    queue="throttle_requests",
    message={
        "action": "release",
        "url": "https://example.com/page",
        "reply_to": "my_response_queue"
    }
)
```

## Environment Variables

- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`: Database connection
- `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`, `REDIS_PASSWORD`: Redis connection (moved to shared)
- `RABBITMQ_HOST`, `RABBITMQ_PORT`, `RABBITMQ_USER`, `RABBITMQ_PASSWORD`, `RABBITMQ_VHOST`: RabbitMQ connection
- `RABBITMQ_THROTTLE_QUEUE`: Queue to consume throttle requests from (default: `throttle_requests`)
- `CONFIG_REFRESH_INTERVAL`: How often to reload domain configs in seconds (default: 60)
- `DEFAULT_REQUESTS_PER_SECOND`: Default rate for unconfigured domains (default: 1.0)
- `DEFAULT_CONCURRENT_REQUESTS`: Default concurrent limit (default: 1)

## Docker

The service is designed to run as a Docker container:

```bash
docker-compose up -d throttling
```

## Dependencies

- `redis`: Distributed state management (in shared)
- `aio-pika`: RabbitMQ async client (in shared)
- `sqlalchemy`: Database ORM (in shared)
- `asyncpg`: Async PostgreSQL driver (in shared)
