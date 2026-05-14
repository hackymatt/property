from typing import Optional
from pydantic import BaseModel, ConfigDict


class _Base(BaseModel):
    model_config = ConfigDict(extra="ignore")


class JobPayload(_Base):
    source: str
    stage: str
    url: str
    domain_name: str
    parent_job_run_id: Optional[str] = None
    metadata: Optional[dict] = None


class SchedulePayload(_Base):
    schedule_id: int
    jobs: list[JobPayload]


class AdPayload(_Base):
    created_at: str
    updated_at: str
    url: str
    advertiser_type: Optional[str] = None
    advertiser_name: Optional[str] = None
    development_name: Optional[str] = None
    investment_state: Optional[str] = None
    investment_estimated_delivery: Optional[str] = None
    market_type: Optional[str] = None
    transaction_type: Optional[str] = None
    free_from: Optional[str] = None


class LocationPayload(_Base):
    city: Optional[str] = None
    district: Optional[str] = None
    subdistrict: Optional[str] = None
    municipality: Optional[str] = None
    county: Optional[str] = None
    postal_code: Optional[str] = None
    province: Optional[str] = None
    street: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class ApartmentPayload(_Base):
    type: str
    area: Optional[float] = None
    price: Optional[float] = None
    price_per_m: Optional[float] = None
    rooms_num: Optional[str] = None
    floor_no: Optional[str] = None
    building_floors_num: Optional[str] = None
    build_year: Optional[int] = None
    construction_status: Optional[str] = None
    building_type: Optional[str] = None
    building_material: Optional[str] = None
    heating_type: Optional[str] = None
    ownership_type: Optional[str] = None
    rent: Optional[float] = None


class DataPayload(_Base):
    ad: AdPayload
    location: LocationPayload
    property: ApartmentPayload
