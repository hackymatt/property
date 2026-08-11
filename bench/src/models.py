"""SQLAlchemy models for bench (reflected from DB, read-only).

Direct DB access, not an API call to crudhouse — per the "no API between
services" rule, bench reads ScraperSourceStage straight from Postgres to
decide what runs next."""

from sqlalchemy.ext.automap import automap_base

Base = automap_base()
ScraperSource = None  # populated after reflect()
ScraperSourceStage = None  # populated after reflect()
JobRunLog = None  # populated after reflect() — read for the RCN hash-gate (see stage_repository.py)
