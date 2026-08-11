from typing import Optional
from pydantic import BaseModel, ConfigDict


class _Base(BaseModel):
    model_config = ConfigDict(extra="ignore")


class JobPayload(_Base):
    source: str
    stage: str
    url: str
    domain_name: str
    # Dotted reference into scraper's STAGE_REGISTRY, e.g. "otodom.ListPagesStage".
    # Always None as built by scheduler — bench resolves and fills it in
    # (both for a schedule's first job and every follow-up) right before
    # publishing to job_exchange, so stage resolution has one owner.
    code_ref: Optional[str] = None
    parent_job_run_id: Optional[str] = None
    # User-configured, per-job input (Job.params), constant for the whole
    # pipeline run. Kept separate from `metadata`, which is runtime state
    # handed from one stage to the next (file paths, hashes, results).
    params: Optional[dict] = None
    metadata: Optional[dict] = None


class SchedulePayload(_Base):
    schedule_id: int
    jobs: list[JobPayload]
    # Only set on the terminal message a schedule run gets when bench decides
    # it is finished (job counts). Empty while the run is being dispatched.
    metadata: Optional[dict] = None


class DataExchangePayload(_Base):
    """Message published to data_exchange for one record ready to land in
    PropertyRaw. Produced by the source's final stage (e.g. GET_ITEM for a
    portal, LOAD for RCN — one LOAD run can emit many of these)."""

    source: str
    job_run_id: Optional[str] = None
    external_ref: str
    data: dict
    property_type: Optional[str] = None  # overrides ScraperSource.property_type when set (RCN: per GPKG layer)
