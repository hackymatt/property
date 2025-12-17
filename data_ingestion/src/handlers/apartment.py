from dataclasses import asdict
from shared.payloads import DataPayload
from src.logger import logger
from src.select_helper import Select
from src.insert_helper import Insert
from src.update_helper import Update
import asyncio
from datetime import datetime, timezone


class ApartmentHandler:
    # Fields to skip by default in change detection
    SKIP_FIELDS = {"last_seen_at", "updated_at", "created_at"}

    @staticmethod
    def normalize_value(val, key=None):
        try:
            return float(val)
        except (ValueError, TypeError):
            return val

    @staticmethod
    def safe_str(val):
        """Convert value to string, datetimes as ISO UTC string."""
        if val is None:
            return None
        return str(val)

    async def detect_and_log_changes(
        self, apartment, apartment_data: dict, skip_fields=None
    ):
        """Detect changes and log them, skipping specified fields."""
        if skip_fields is None:
            skip_fields = self.SKIP_FIELDS
        tasks = []
        for key, value in apartment_data.items():
            if key in skip_fields:
                continue
            current_value = self.normalize_value(getattr(apartment, key), key)
            new_value = self.normalize_value(value, key)
            if current_value != new_value:
                change_data = {
                    "listing_id": apartment.id,
                    "field_name": key,
                    "old_value": self.safe_str(current_value),
                    "new_value": self.safe_str(new_value),
                }
                tasks.append(self.insert.apartment_listing_change(change_data))
        if tasks:
            await asyncio.gather(*tasks)

    def __init__(self, db, schedule_run_id, job_run_id):
        self.db = db
        self.select = Select(db, logger, schedule_run_id, job_run_id)
        self.insert = Insert(db, logger, schedule_run_id, job_run_id)
        self.update = Update(db, logger, schedule_run_id, job_run_id)

    async def handle(self, payload: DataPayload):
        ad = payload.ad
        location = payload.location
        property = payload.property

        ad_data = asdict(ad)
        location_data = asdict(location)
        property_data = asdict(property)

        await asyncio.gather(
            self.insert.location(location_data),
            self.insert.advertiser_type(ad.advertiser_type),
            self.insert.advertiser_name(ad.advertiser_name),
            self.insert.development_name(ad.development_name),
            self.insert.market_type(ad.market_type),
            self.insert.transaction_type(ad.transaction_type),
            self.insert.property_type(property.type),
            self.insert.room(property.rooms_num),
            self.insert.floor(property.floor_no),
            self.insert.building_floor(property.building_floors_num),
            self.insert.construction_status(property.construction_status),
            self.insert.building_type(property.building_type),
            self.insert.building_material(property.building_material),
            self.insert.heating_type(property.heating_type),
            self.insert.ownership_type(property.ownership_type),
        )

        apartment_data = {
            **{
                **ad_data,
                "created_at": datetime.strptime(ad.created_at, "%Y-%m-%dT%H:%M:%S%z"),
                "updated_at": datetime.strptime(ad.updated_at, "%Y-%m-%dT%H:%M:%S%z"),
            },
            **location_data,
            **property_data,
            "last_seen_at": datetime.now(timezone.utc),
        }
        apartment = await self.select.apartment(ad.url)
        if not apartment:
            await self.insert.apartment_listing(apartment_data)
            logger.info(
                f"[DATA_INGESTION] Inserted ApartmentListing for schedule_run_id={self.select.schedule_run_id} job_run_id={self.select.job_run_id}"
            )
            return

        # Detect and log changes, skipping default fields
        await self.detect_and_log_changes(apartment, apartment_data)

        # Update if apartment already exists
        await self.update.apartment_listing(apartment_data)
