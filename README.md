# Property Data Hub

A microservices platform for scraping and ingesting raw property data (Otodom listings today, RCN transactions next) into `PropertyRaw` — a single, insert-only landing table. Stage handler logic lives as versioned Python classes in the `scraper` repo, not as database-stored snippets; the database only holds *which* stages a source runs through and in what order.

## Architecture

```
Browser → nginx (:80)
              ├── /api/*  → crudhouse (Django + DRF, admin-only — no service calls it)
              ├── /admin/ → crudhouse
              └── /*      → ui (Next.js) — currently out of scope, see plan

scheduler → RabbitMQ (schedule_exchange) → bench ─┐
                                                    │ resolves code_ref via
                                                    │ ScraperSourceStage (direct
                                                    │ DB read, no API calls)
                                                    ▼
                                    job_exchange → scraper → throttling
                                        ▲               │
                                        │ next stage     │ status (+result)
                                        └──── bench ◄────┘
                                                │ last stage → forward record(s)
                                                ▼
                                       data_exchange → data-ingestion → PropertyRaw
                                                                            ▲
                                                                       (owned by crudhouse)
```

`bench` is the stateless stage orchestrator: it never executes a stage itself, only decides — by reading `ScraperSourceStage` order — whether a job's result becomes the next stage's jobs or a final record forwarded to `data-ingestion`. No service calls another service's API; the only inter-service channels are RabbitMQ and direct, least-privilege reads of the shared Postgres database.

### Services

| Service | Description |
|---|---|
| **nginx** | Reverse proxy — single entry point on port 80 |
| **crudhouse** | Django app — owns the schema: Domains / Sources+Stages / Jobs / Schedules / run logs / `PropertyRaw`. Admin-only REST API. |
| **scheduler** | Reads active Schedules from DB, publishes `SchedulePayload`s to RabbitMQ at cron times |
| **bench** | Stateless stage orchestrator — fans schedules into jobs and jobs into their next stage (or into `data_exchange` on the last stage), based on `ScraperSourceStage` |
| **scraper** | Executes exactly one stage per job (a `Stage` class resolved by `code_ref`), publishes its result — never decides what runs next |
| **throttling** | Per-domain rate limiter (token bucket + concurrency cap, Redis-backed), used by every HTTP-fetching stage |
| **data-ingestion** | Consumes `data_exchange`, writes insert-only to `PropertyRaw` (idempotent via `ON CONFLICT DO NOTHING`) |
| **logger** | Listens to job/schedule exchanges and persists run logs |

`ui/` and `data-hub/` are out of scope for the current phase — see `docs/adr` / the architecture plan for what's deliberately deferred and why.

### Scraper pipeline stages

Stages are per-`ScraperSource.source_kind`, not a single fixed pipeline:

```
PORTAL_LISTING (Otodom)  LIST_PAGES → LIST_ITEMS → GET_ITEM
FILE_REGISTRY (RCN)      DISCOVER → DOWNLOAD → EXTRACT → TRANSFORM → LOAD
```

For `FILE_REGISTRY` sources, stages hand binary/bulk artifacts to each other via a **shared, ephemeral scratch volume** (`RCN_SCRATCH_DIR`, mounted on every `scraper` replica) rather than through RabbitMQ messages — only paths travel in the payload. The volume needs no durability: RCN files are cumulative, so a lost artifact just costs one re-download.

`DISCOVER` fingerprints each file cheaply (HEAD + hash of the first 64 KB) and `bench` compares that against the fingerprint of the **last successful `LOAD`** — so an unchanged file is never downloaded at all, while a run that failed partway through gets fully retried on the next cycle.

Each stage is a `Stage` subclass under `scraper/src/sources/<name>/stages.py`, registered in `scraper/src/stage_registry.py`. `ScraperSourceStage` rows (managed via Django admin) declare, per source, the `stage_name` → `order` → `code_ref` mapping — the database is a registry, never executable code.

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

Adding or changing a source's scraping logic requires a `scraper` deploy — the database only stores configuration, not code (see plan ADR-1). Steps:

1. **Create a Domain** — Admin UI → Domains → Add Domain (e.g. `otodom.pl`, set rate limits)
2. **Write the Stage classes** — under `scraper/src/sources/<name>/stages.py`, one `Stage` subclass per pipeline step (see `scraper/src/sources/otodom/stages.py` for a working example), and register each in `scraper/src/stage_registry.py::STAGE_REGISTRY`
3. **Create a Scraper Source** — Admin UI → Sources → Add Source: `source_kind` (`PORTAL_LISTING`/`FILE_REGISTRY`), `property_type`, `offer_url_prefix` (portal sources)
4. **Register its stages** — inline on the Source form: `stage_name` / `order` / `code_ref` per stage, matching what you registered in `STAGE_REGISTRY`
5. **Create a Job** — Admin UI → Jobs → Add Job (link domain + source, set `stage` to the *first* `stage_name`, paste the starting URL). Scope that the URL can't express goes in **`params`** (JSON), passed to the first stage — e.g. RCN takes `{"teryt_codes": ["1261"]}` for one county or `{"teryt_codes": "all"}` for the whole country, so one Source serves both via different Jobs
6. **Create a Schedule** — Admin UI → Schedules → Add Schedule (cron expression, attach the job)

The scheduler fires the job at the next cron time; `bench` resolves each stage's `code_ref` and advances the pipeline automatically based on `ScraperSourceStage` order.

### Stage context

Every `Stage.run(ctx)` receives a `StageContext` with:

| Name | Description |
|---|---|
| `ctx.url` | The URL/ref being processed for this stage |
| `ctx.params` | `Job.params` — user-configured input, constant for the whole run (RCN reads its TERYT scope here) |
| `ctx.fetch(url, method, **kwargs)` | Async HTTP helper (throttled automatically via the shared `throttling` service) |
| `ctx.domain_name` | The source's `Domain.name`, for throttling |
| `ctx.offer_url_prefix` | Configured base URL for item links (portal sources) |
| `ctx.metadata` | Free-form dict carried over from the job payload (e.g. RCN passes file paths/hashes between stages here) |

A non-final stage returns `list[str]` — refs for the next stage. The final stage (no following `ScraperSourceStage`) returns `list[RawItem]` (`external_ref`, `data`, optional `property_type` override) — one per record ready to land in `PropertyRaw`.

## Project structure

```
├── nginx/                # Reverse proxy config
├── crudhouse/             # Django REST API + admin — owns the schema
│   ├── api/                # DRF viewsets (admin-only, no service calls it)
│   ├── scraper_source/     # ScraperSource + ScraperSourceStage (registry, not code)
│   └── property_raw/       # PropertyRaw — the one domain data model this phase
├── scraper/                # Stage execution engine
│   └── src/
│       ├── stages/base.py       # Stage / StageContext / RawItem contracts
│       ├── sources/otodom/      # Stage classes per source
│       ├── stage_registry.py    # code_ref -> Stage class
│       ├── source_loader.py     # DB-backed source config cache (5 min TTL)
│       └── deduplicator.py      # Redis dedup (SET NX per source+stage+url)
├── bench/                 # Stateless stage orchestrator (schedule fan-out + stage advancement)
├── scheduler/              # Cron-based job dispatcher
├── throttling/              # Token bucket rate limiter
├── data-ingestion/           # Insert-only PropertyRaw writer
├── logger/                    # Run log writer
├── shared/                     # Common code (RabbitMQ, DB, Redis, payloads)
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

## Deduplication

Duplicates are prevented where it actually matters — in the data, not in the queue:

`property_raw` has a unique constraint on `(source_id, external_ref, content_hash)` and every write is an `INSERT ... ON CONFLICT DO NOTHING`. Re-ingesting unchanged content is a no-op; genuinely changed content inserts a new row, which is what builds the history. Photo downloads are guarded the same way by `storage.exists()`.

There is deliberately **no** job-level Redis dedup cache. It only avoided repeating work, never protected integrity, and its 7-day TTL on `get_item` actively prevented detecting price changes — the opposite of what a historical database is for. Re-crawl frequency belongs to per-listing scheduling (`next_crawl_at`), not to a blunt cache TTL.
