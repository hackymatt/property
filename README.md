# Property Scraping Platform

A microservices platform for scraping and storing property listings (e.g. Otodom). Scraper logic is stored as Python code snippets in the database — no deployment needed to add or update a source.

## Architecture

```
Browser → nginx (:80)
              ├── /api/*  → crudhouse (Django + DRF)
              ├── /admin/ → crudhouse
              └── /*      → ui (Next.js)

scheduler → RabbitMQ → scraper → throttling (rate limiter)
                               ↓
                         data_ingestion → PostgreSQL
                               ↓
                            logger
```

### Services

| Service | Description |
|---|---|
| **nginx** | Reverse proxy — single entry point on port 80 |
| **ui** | Next.js admin UI (AG Grid tables, Monaco code editors) |
| **crudhouse** | Django app — REST API + Django admin, manages Domains / Sources / Jobs / Schedules |
| **scheduler** | Reads active Schedules from DB, publishes Jobs to RabbitMQ at cron times |
| **scraper** | Consumes jobs, executes user-defined Python snippets, fans out follow-up jobs |
| **throttling** | Per-domain rate limiter (token bucket + concurrency cap, Redis-backed) |
| **data_ingestion** | Receives scraped DataPayloads from RabbitMQ and writes to PostgreSQL |
| **logger** | Listens to job/schedule exchanges and persists run logs |
| **bench** | Benchmarking / load testing tool |

### Scraper pipeline stages

Each scrape runs through three stages, each a separate RabbitMQ job:

```
list_pages  →  list_items  →  get_item  →  data_ingestion
```

Source logic for each stage is stored as Python code snippets in the `ScraperSource` model and executed dynamically at runtime.

## Quick start

### Prerequisites

- Docker and Docker Compose

### Setup

```bash
git clone <repository-url>
cd property
cp .env.example .env   # edit secrets before running in production
docker compose up --build
```

### Access

| URL | What |
|---|---|
| `http://localhost` | Admin UI (login with superuser credentials) |
| `http://localhost/admin/` | Django admin |
| `http://localhost:15672` | RabbitMQ management (rabbit / rabbit) |

Default superuser: **admin / admin** (set via `SUPERUSER_USERNAME` / `SUPERUSER_PASSWORD` in `.env`).

## Configuration

All configuration is via `.env`. Copy `.env.example` and fill in the values:

```bash
cp .env.example .env
```

Key variables:

| Variable | Description | Default |
|---|---|---|
| `DJANGO_SECRET_KEY` | Django secret key — change in production | — |
| `DB_*` | PostgreSQL connection | `db:5432` |
| `RABBITMQ_*` | RabbitMQ connection + queue/exchange names | `rabbitmq:5672` |
| `REDIS_*` | Redis connection | `redis:6379` |
| `SUPERUSER_*` | Django admin credentials | admin / admin |

> **Note:** `DB_HOST`, `RABBITMQ_HOST`, `REDIS_HOST` should be the docker-compose service names (`db`, `rabbitmq`, `redis`) when running in Docker. Use `localhost` for local development outside Docker.

## Adding a scraper source

1. **Create a Domain** — Admin UI → Domains → Add Domain (e.g. `otodom.pl`, set rate limits)
2. **Create a Scraper Source** — Admin UI → Sources → Add Source, fill in the four Python snippets:
   - **Preamble** — shared helpers and imports
   - **List Pages** — returns `List[str]` of paginated URLs
   - **List Items** — returns `List[str]` of item detail URLs
   - **Get Item** — returns a `DataPayload` instance
3. **Create a Job** — Admin UI → Jobs → Add Job (link domain + source, set stage to `list_pages`, paste the starting URL)
4. **Create a Schedule** — Admin UI → Schedules → Add Schedule (cron expression, attach the job)

The scheduler will fire the job at the next cron time and the scraper will process it automatically.

### Snippet context

Every snippet has access to:

| Name | Description |
|---|---|
| `url` | The URL being processed |
| `fetch(url, method, **kwargs)` | Async HTTP helper (throttled automatically) |
| `OFFER_URL_PREFIX` | Configured base URL for item links |
| `deep_get(dct, keys)` | Safe nested dict accessor |
| `get_first(lst)` | Returns `lst[0]` or `None` |
| `AdPayload`, `LocationPayload`, `ApartmentPayload`, `DataPayload` | Payload constructors |
| `json`, `asyncio` | Standard library |

## Project structure

```
├── nginx/                # Reverse proxy config
├── ui/                   # Next.js admin frontend
├── crudhouse/            # Django REST API + admin
│   └── api/              # DRF viewsets (domains, sources, jobs, schedules)
├── scraper/              # Scraping engine
│   └── src/
│       ├── dynamic_scraper.py   # Snippet executor
│       ├── source_loader.py     # DB-backed source cache (5 min TTL)
│       └── deduplicator.py      # Redis dedup (SET NX per source+stage+url)
├── scheduler/            # Cron-based job dispatcher
├── throttling/           # Token bucket rate limiter
├── data_ingestion/       # Scraped data writer
├── logger/               # Run log writer
├── shared/               # Common code (RabbitMQ, DB, Redis, payloads)
├── bench/                # Benchmarking
├── docker-compose.yml
├── .env.example
└── .env                  # gitignored
```

## Rate limiting & 429 handling

Rate limits are configured per domain in the Admin UI (Domains → edit):

- **Requests per second** — token refill rate
- **Burst capacity** — max tokens in bucket
- **Concurrent requests** — max simultaneous in-flight requests

When the scraper receives a 429 response it:
1. Sends a `pause` signal to the throttle service (respects `Retry-After` header, defaults to 60 s)
2. Clears the dedup key for the failed job
3. Requeues the job — it will wait in the throttle queue until the pause expires

## Job deduplication

The scraper uses Redis `SET NX` to deduplicate jobs by `(source, stage, url)`:

- `list_pages` / `list_items` — 1 hour TTL
- `get_item` — 7 day TTL

Duplicate incoming jobs are silently dropped. Duplicate URLs in follow-up batches are filtered before publishing. On 429 requeue the dedup key is cleared so the job can retry.
