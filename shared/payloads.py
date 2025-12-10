from dataclasses import dataclass
from typing import List, Optional

from shared.consts import Status


@dataclass
class ScheduleJob:
    source: str
    stage: str
    url: str
    domain: Optional[str]


@dataclass
class SchedulePayload:
    schedule_id: int
    jobs: List[ScheduleJob]
