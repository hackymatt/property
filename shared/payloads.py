from dataclasses import dataclass
from typing import List, Optional


@dataclass
class JobPayload:
    source: str
    stage: str
    url: str
    domain_name: str
    parent_job_run_id: Optional[str] = None
    metadata: Optional[dict] = None


@dataclass
class SchedulePayload:
    schedule_id: int
    jobs: List[JobPayload]
