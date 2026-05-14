from datetime import datetime, timezone

from shared.payloads import DataPayload
from src.logger import logger
from src.select_helper import Select
from src.insert_helper import Insert
from src.update_helper import Update


class ApartmentHandler:
    SKIP_FIELDS = {"last_seen_at", "updated_at", "created_at"}

    def __init__(self, db, schedule_run_id, job_run_id):
        self.db = db
        self.select = Select(db, logger, schedule_run_id, job_run_id)
        self.insert = Insert(db, logger, schedule_run_id, job_run_id)
        self.update = Update(db, logger, schedule_run_id, job_run_id)

    @staticmethod
    def _normalize(val):
        try:
            return float(val)
        except (ValueError, TypeError):
            return val

    @staticmethod
    def _safe_str(val):
        return None if val is None else str(val)

    async def _detect_and_log_changes(self, session, apartment, apartment_data: dict):
        for key, value in apartment_data.items():
            if key in self.SKIP_FIELDS:
                continue
            current = self._normalize(getattr(apartment, key, None))
            new = self._normalize(value)
            if current != new:
                await self.insert.apartment_listing_change(
                    {
                        "listing_id": apartment.id,
                        "field_name": key,
                        "old_value": self._safe_str(current),
                        "new_value": self._safe_str(new),
                    },
                    session=session,
                )

    async def handle(self, payload: DataPayload):
        ad = payload.ad
        location = payload.location
        property = payload.property

        ad_data = ad.model_dump()
        location_data = location.model_dump()
        property_data = property.model_dump()

        # Phase 1: idempotent lookup inserts — single session, sequential
        # (asyncio.gather + shared session is unsafe in SQLAlchemy async)
        async with self.db.get_session() as session:
            async with session.begin():
                await self.insert.location(location_data, session=session)
                await self.insert.advertiser_type(ad.advertiser_type, session=session)
                await self.insert.advertiser_name(ad.advertiser_name, session=session)
                await self.insert.development_name(ad.development_name, session=session)
                await self.insert.investment_state(ad.investment_state, session=session)
                await self.insert.market_type(ad.market_type, session=session)
                await self.insert.transaction_type(ad.transaction_type, session=session)
                await self.insert.property_type(property.type, session=session)
                await self.insert.room(property.rooms_num, session=session)
                await self.insert.floor(property.floor_no, session=session)
                await self.insert.building_floor(property.building_floors_num, session=session)
                await self.insert.construction_status(property.construction_status, session=session)
                await self.insert.building_type(property.building_type, session=session)
                await self.insert.building_material(property.building_material, session=session)
                await self.insert.heating_type(property.heating_type, session=session)
                await self.insert.ownership_type(property.ownership_type, session=session)

        apartment_data = {
            **ad_data,
            "free_from": (
                datetime.strptime(ad.free_from, "%Y-%m-%d").date() if ad.free_from else None
            ),
            "created_at": datetime.strptime(ad.created_at, "%Y-%m-%dT%H:%M:%S%z"),
            "updated_at": datetime.strptime(ad.updated_at, "%Y-%m-%dT%H:%M:%S%z"),
            **location_data,
            **property_data,
            "last_seen_at": datetime.now(timezone.utc),
        }

        # Phase 2: atomic select → insert/update in a single transaction
        async with self.db.get_session() as session:
            async with session.begin():
                apartment = await self.select.apartment(ad.url, session=session)
                if apartment is None:
                    await self.insert.apartment_listing(apartment_data, session=session)
                    logger.info(
                        f"[DATA_INGESTION] Inserted ApartmentListing for schedule_run_id={self.select.schedule_run_id} job_run_id={self.select.job_run_id}"
                    )
                else:
                    await self._detect_and_log_changes(session, apartment, apartment_data)
                    await self.update.apartment_listing(apartment_data, session=session)
