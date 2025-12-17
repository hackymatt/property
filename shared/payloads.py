from dataclasses import dataclass
from typing import List, Optional
from enum import Enum


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


@dataclass
class AdPayload:
    created_at: str
    updated_at: str
    advertiser_type: str
    advertiser_name: Optional[str]
    development_name: Optional[str]
    url: str
    market_type: str
    transaction_type: str


@dataclass
class LocationPayload:
    city: str
    district: Optional[str]
    subdistrict: Optional[str]
    municipality: Optional[str]
    county: Optional[str]
    postal_code: Optional[str]
    province: Optional[str]
    street: Optional[str]
    latitude: float
    longitude: float


@dataclass
class ApartmentPayload:
    type: str
    area: float
    price: Optional[float]
    price_per_m: Optional[float]
    rooms_num: str
    floor_no: str
    building_floors_num: str
    build_year: int
    construction_status: str
    building_type: str
    building_material: Optional[str]
    heating_type: str
    ownership_type: str
    rent: Optional[float]


@dataclass
class DataPayload:
    ad: AdPayload
    location: LocationPayload
    property: ApartmentPayload
