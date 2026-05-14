"""Configuration for scraper service"""

import os
from dotenv import load_dotenv

load_dotenv()

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "rabbit")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD", "rabbit")
RABBITMQ_VHOST = os.getenv("RABBITMQ_VHOST", "/")
RABBITMQ_JOB_QUEUE = os.getenv("RABBITMQ_JOB_QUEUE", "scraper_jobs")
RABBITMQ_JOB_EXCHANGE = os.getenv("RABBITMQ_JOB_EXCHANGE", "job_exchange")
RABBITMQ_DATA_EXCHANGE = os.getenv("RABBITMQ_DATA_EXCHANGE", "data_exchange")
RABBITMQ_EXCHANGE_TYPE = os.getenv("RABBITMQ_EXCHANGE_TYPE", "topic")
RABBITMQ_ROUTING_KEY = os.getenv("RABBITMQ_ROUTING_KEY", "job.*.*.pending")

# Throttling service
RABBITMQ_THROTTLE_QUEUE = os.getenv("RABBITMQ_THROTTLE_QUEUE", "throttle_requests")

STARTUP_RETRIES = int(os.getenv("STARTUP_RETRIES", "5"))
STARTUP_RETRY_DELAY = int(os.getenv("STARTUP_RETRY_DELAY", "5"))

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)

DB_HOST = os.getenv("DB_HOST", "db")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "property")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
