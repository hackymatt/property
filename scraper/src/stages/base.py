"""Base contract for stage classes.

A Stage executes exactly one unit of work for one ScraperSource and never
decides what runs next — that orchestration lives in `bench`, which reads
the stage order from ScraperSourceStage (crudhouse DB) after seeing this
stage's result. Adding a new source or stage is: write a Stage subclass,
register it in stage_registry.STAGE_REGISTRY, deploy, then add a
ScraperSourceStage row pointing at it — no database-stored/exec()'d code.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Awaitable, Callable, Optional, Union


@dataclass
class StageContext:
    """Everything a Stage needs to execute, built fresh per job."""

    url: str
    domain_name: str
    offer_url_prefix: str
    fetch: Callable[..., Awaitable[dict]]
    throttle_helper: object  # shared.throttle_helper.ThrottleHelper — for stages that need raw/binary HTTP (see sources/rcn/geoportal.py)
    # Publishes ONE record downstream, immediately. Final stages call this
    # per record instead of returning them: a list of N records would have
    # to cross RabbitMQ (and land in JobRunLog) as a single message, which
    # for a 20k-row RCN layer is megabytes. See RawItem.
    emit: Callable[["RawItem"], Awaitable[None]]
    # What the source IS (ScraperSource.config) — e.g. which GPKG layer this
    # RCN source reads. Same for every job of the source.
    source_config: dict = field(default_factory=dict)
    # What this RUN covers (Job.params) — e.g. which TERYT codes to check.
    params: dict = field(default_factory=dict)
    # Runtime state handed over from the previous stage (file paths, hashes).
    metadata: dict = field(default_factory=dict)


@dataclass
class NextStageRef:
    """One follow-up job for the next stage. `metadata` carries whatever
    state needs to survive the hop (e.g. RCN passes file_id/fingerprint/
    partial results between DISCOVER->DOWNLOAD->EXTRACT->TRANSFORM->LOAD,
    since each stage is a separate job that may land on a different
    scraper replica). A bare `str` is shorthand for `NextStageRef(url=str,
    metadata={})` — that's all portal stages (Otodom) need."""

    url: str
    metadata: dict = field(default_factory=dict)


@dataclass
class RawItem:
    """One record ready to land in PropertyRaw. Handed to ctx.emit() one at a
    time — never returned in bulk, so no message ever carries a batch."""

    external_ref: str
    data: dict
    property_type: Optional[str] = None


# Stages return refs for bench to fan out into follow-up jobs. A final stage
# returns an empty list and emits its records instead.
StageResult = Union[list[str], list[NextStageRef]]


class Stage(ABC):
    @abstractmethod
    async def run(self, ctx: StageContext) -> StageResult:
        raise NotImplementedError
