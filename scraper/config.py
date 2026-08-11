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
# Final stages publish one message per record here (see src/scrape.py::emit).
RABBITMQ_DATA_EXCHANGE = os.getenv("RABBITMQ_DATA_EXCHANGE", "data_exchange")
RABBITMQ_EXCHANGE_TYPE = os.getenv("RABBITMQ_EXCHANGE_TYPE", "topic")
RABBITMQ_ROUTING_KEY = os.getenv("RABBITMQ_ROUTING_KEY", "job.*.*.pending")

# Throttling service
RABBITMQ_THROTTLE_QUEUE = os.getenv("RABBITMQ_THROTTLE_QUEUE", "throttle_requests")

STARTUP_RETRIES = int(os.getenv("STARTUP_RETRIES", "5"))
STARTUP_RETRY_DELAY = int(os.getenv("STARTUP_RETRY_DELAY", "5"))

# No Redis here: the scraper used to keep a job-dedup cache, but duplicate
# ROWS are prevented by PropertyRaw's unique constraint, and re-crawl
# frequency belongs to per-listing scheduling, not a blunt TTL.
# Redis is still used by the throttling service for its token buckets.

# Shared, ephemeral scratch volume for binary artifacts that don't fit in a
# RabbitMQ message (RCN zip/gpkg files) — mounted at the same path on every
# scraper replica. No durability requirement: RCN files are cumulative, so
# a lost/corrupt scratch file just means the next DISCOVER cycle re-downloads
# it (see plan section 3.3).
RCN_SCRATCH_DIR = os.getenv("RCN_SCRATCH_DIR", "/data/rcn_scratch")

# Durable blob storage for scraped binaries (listing photos). Unlike the RCN
# scratch volume this one must NOT be wiped — the photos are the product.
# Swapped for S3 later, see src/sdk/storage.py.
PHOTO_STORAGE_DIR = os.getenv("PHOTO_STORAGE_DIR", "/data/photos")

DB_HOST = os.getenv("DB_HOST", "db")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "property")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
