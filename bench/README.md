# Bench Service

The stateless stage orchestrator. Two responsibilities, both pure message
routing (no domain logic beyond "what stage comes next", read from
`ScraperSourceStage` via a direct, read-only DB connection — never an API
call to crudhouse):

1. **Schedule fan-out** — consumes `SchedulePayload`s published by
   `scheduler` on `schedule_exchange`, resolves each job's `code_ref` and
   publishes it to `job_exchange`.
2. **Stage advancement** — consumes job status events on `job_exchange`.
   On `SUCCESS`, looks up the next `ScraperSourceStage` for that source: if
   there is one, publishes a follow-up job per ref in the result; if not
   (this was the last stage), forwards each result record to
   `data_exchange` for `data-ingestion` to land in `PropertyRaw`.

Holds no state between messages — any number of replicas can consume the
same queues interchangeably.

## Usage

- Build and run with Docker Compose:
  ```sh
  docker-compose up -d --build bench
  ```

## Environment Variables

- `RABBITMQ_HOST` / `RABBITMQ_PORT` / `RABBITMQ_USER` / `RABBITMQ_PASSWORD` / `RABBITMQ_VHOST`
- `RABBITMQ_SCHEDULE_QUEUE` / `RABBITMQ_SCHEDULE_EXCHANGE` / `RABBITMQ_SCHEDULE_ROUTING_KEY`
- `RABBITMQ_JOB_EXCHANGE` / `RABBITMQ_JOB_STATUS_QUEUE` / `RABBITMQ_JOB_STATUS_ROUTING_KEY`
- `RABBITMQ_DATA_EXCHANGE`
- `DB_HOST` / `DB_PORT` / `DB_NAME` / `DB_USER` / `DB_PASSWORD` — read-only access to `scraper_source` / `scraper_source_stage`
