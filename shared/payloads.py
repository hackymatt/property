from dataclasses import dataclass
from typing import List, Optional


@dataclass
class JobPayload:
    job_id: int
    source: str
    stage: str
    url: str
    domain: Optional[str]


@dataclass
class SchedulePayload:
    schedule_id: int
    jobs: List[JobPayload]
