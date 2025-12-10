# Bench Service

A simple Python service subscribing to the RabbitMQ `schedule` queue. No database required.

## Usage

- Build and run with Docker Compose:
  ```sh
  docker-compose up -d --build bench
  ```
- The service listens for messages on the `schedule` queue and prints them.

## Environment Variables

- `RABBITMQ_HOST`
- `RABBITMQ_PORT`
- `RABBITMQ_USER`
- `RABBITMQ_PASSWORD`
- `RABBITMQ_VHOST`
- `RABBITMQ_SCHEDULE_QUEUE`

## Extending

- Add logic in `main.py` or `src/bench.py` as needed.
