"""Configuration for bench service"""

import os
from dotenv import load_dotenv

load_dotenv()

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "rabbit")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD", "rabbit")
RABBITMQ_VHOST = os.getenv("RABBITMQ_VHOST", "/")
RABBITMQ_EXCHANGE_TYPE = os.getenv("RABBITMQ_EXCHANGE_TYPE", "topic")

# Schedule exchange: scheduler -> bench, fans out into individual job_exchange jobs.
RABBITMQ_SCHEDULE_QUEUE = os.getenv("RABBITMQ_SCHEDULE_QUEUE", "bench_schedule")
RABBITMQ_SCHEDULE_EXCHANGE = os.getenv("RABBITMQ_SCHEDULE_EXCHANGE", "schedule_exchange")
RABBITMQ_SCHEDULE_ROUTING_KEY = os.getenv("RABBITMQ_SCHEDULE_ROUTING_KEY", "schedule.*.pending")

# Job exchange: scraper -> bench (status events). Bench reacts to terminal
# statuses only (SUCCESS / SUCCESS_NO_CHANGE) — pending/running/failed are
# ignored here (failed jobs are just logged elsewhere; scraper handles its
# own retriable-error requeue).
RABBITMQ_JOB_EXCHANGE = os.getenv("RABBITMQ_JOB_EXCHANGE", "job_exchange")
RABBITMQ_JOB_STATUS_QUEUE = os.getenv("RABBITMQ_JOB_STATUS_QUEUE", "bench_job_status")
RABBITMQ_JOB_STATUS_ROUTING_KEY = os.getenv("RABBITMQ_JOB_STATUS_ROUTING_KEY", "job.*.*.*")

# Data exchange: bench -> data-ingestion, one message per final-stage record.
RABBITMQ_DATA_EXCHANGE = os.getenv("RABBITMQ_DATA_EXCHANGE", "data_exchange")

STARTUP_RETRIES = int(os.getenv("STARTUP_RETRIES", "5"))
STARTUP_RETRY_DELAY = int(os.getenv("STARTUP_RETRY_DELAY", "5"))

DB_HOST = os.getenv("DB_HOST", "db")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "property")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
