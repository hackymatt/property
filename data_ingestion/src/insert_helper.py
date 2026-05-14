from contextlib import asynccontextmanager
from src.db_utils import insert_ignore
from src import models
from datetime import datetime, timezone


class Insert:
    def __init__(self, db, logger, schedule_run_id, job_run_id):
        self.db = db
        self.logger = logger
        self.schedule_run_id = schedule_run_id
        self.job_run_id = job_run_id

    def _add_base_fields(self, data: dict) -> dict:
        now = datetime.now(timezone.utc)
        data_copy = data.copy()
        data_copy["created_at"] = now
        data_copy["updated_at"] = now
        return data_copy

    @asynccontextmanager
    async def _session(self, session=None):
        """Yield an active session. Uses caller's session if provided, otherwise opens
        a new one with its own transaction."""
        if session is not None:
            yield session
        else:
            async with self.db.get_session() as s:
                async with s.begin():
                    yield s

    async def location(self, location_data, session=None):
        if not location_data:
            return
        async with self._session(session) as s:
            await insert_ignore(
                s, models.Location, self._add_base_fields(location_data), ["latitude", "longitude"]
            )
        self.logger.info(
            f"[DATA_INGESTION] Inserted Location for schedule_run_id={self.schedule_run_id} job_run_id={self.job_run_id} (ignored if duplicate)"
        )

    async def advertiser_type(self, advertiser_type, session=None):
        if not advertiser_type:
            return
        async with self._session(session) as s:
            await insert_ignore(
                s, models.AdvertiserType, self._add_base_fields({"name": advertiser_type}), ["name"]
            )
        self.logger.info(
            f"[DATA_INGESTION] Inserted AdvertiserType '{advertiser_type}' for schedule_run_id={self.schedule_run_id} job_run_id={self.job_run_id} (ignored if duplicate)"
        )

    async def advertiser_name(self, advertiser_name, session=None):
        if not advertiser_name:
            return
        async with self._session(session) as s:
            await insert_ignore(
                s, models.AdvertiserName, self._add_base_fields({"name": advertiser_name}), ["name"]
            )
        self.logger.info(
            f"[DATA_INGESTION] Inserted AdvertiserName '{advertiser_name}' for schedule_run_id={self.schedule_run_id} job_run_id={self.job_run_id} (ignored if duplicate)"
        )

    async def development_name(self, development_name, session=None):
        if not development_name:
            return
        async with self._session(session) as s:
            await insert_ignore(
                s, models.DevelopmentName, self._add_base_fields({"name": development_name}), ["name"]
            )
        self.logger.info(
            f"[DATA_INGESTION] Inserted DevelopmentName '{development_name}' for schedule_run_id={self.schedule_run_id} job_run_id={self.job_run_id} (ignored if duplicate)"
        )

    async def investment_state(self, investment_state, session=None):
        if not investment_state:
            return
        async with self._session(session) as s:
            await insert_ignore(
                s, models.InvestmentState, self._add_base_fields({"name": investment_state}), ["name"]
            )
        self.logger.info(
            f"[DATA_INGESTION] Inserted InvestmentState '{investment_state}' for schedule_run_id={self.schedule_run_id} job_run_id={self.job_run_id} (ignored if duplicate)"
        )

    async def market_type(self, market_type, session=None):
        if not market_type:
            return
        async with self._session(session) as s:
            await insert_ignore(
                s, models.MarketType, self._add_base_fields({"name": market_type}), ["name"]
            )
        self.logger.info(
            f"[DATA_INGESTION] Inserted MarketType '{market_type}' for schedule_run_id={self.schedule_run_id} job_run_id={self.job_run_id} (ignored if duplicate)"
        )

    async def transaction_type(self, transaction_type, session=None):
        if not transaction_type:
            return
        async with self._session(session) as s:
            await insert_ignore(
                s, models.TransactionType, self._add_base_fields({"name": transaction_type}), ["name"]
            )
        self.logger.info(
            f"[DATA_INGESTION] Inserted TransactionType '{transaction_type}' for schedule_run_id={self.schedule_run_id} job_run_id={self.job_run_id} (ignored if duplicate)"
        )

    async def property_type(self, property_type, session=None):
        if not property_type:
            return
        async with self._session(session) as s:
            await insert_ignore(
                s, models.PropertyType, self._add_base_fields({"name": property_type}), ["name"]
            )
        self.logger.info(
            f"[DATA_INGESTION] Inserted PropertyType '{property_type}' for schedule_run_id={self.schedule_run_id} job_run_id={self.job_run_id} (ignored if duplicate)"
        )

    async def room(self, rooms_num, session=None):
        if rooms_num is None:
            return
        async with self._session(session) as s:
            await insert_ignore(
                s, models.Room, self._add_base_fields({"name": str(rooms_num)}), ["name"]
            )
        self.logger.info(
            f"[DATA_INGESTION] Inserted Room '{rooms_num}' for schedule_run_id={self.schedule_run_id} job_run_id={self.job_run_id} (ignored if duplicate)"
        )

    async def floor(self, floor_no, session=None):
        if floor_no is None:
            return
        async with self._session(session) as s:
            await insert_ignore(
                s, models.Floor, self._add_base_fields({"name": str(floor_no)}), ["name"]
            )
        self.logger.info(
            f"[DATA_INGESTION] Inserted Floor '{floor_no}' for schedule_run_id={self.schedule_run_id} job_run_id={self.job_run_id} (ignored if duplicate)"
        )

    async def building_floor(self, building_floors_num, session=None):
        if building_floors_num is None:
            return
        async with self._session(session) as s:
            await insert_ignore(
                s, models.BuildingFloor, self._add_base_fields({"name": str(building_floors_num)}), ["name"]
            )
        self.logger.info(
            f"[DATA_INGESTION] Inserted BuildingFloor '{building_floors_num}' for schedule_run_id={self.schedule_run_id} job_run_id={self.job_run_id} (ignored if duplicate)"
        )

    async def construction_status(self, construction_status, session=None):
        if not construction_status:
            return
        async with self._session(session) as s:
            await insert_ignore(
                s, models.ConstructionStatus, self._add_base_fields({"name": construction_status}), ["name"]
            )
        self.logger.info(
            f"[DATA_INGESTION] Inserted ConstructionStatus '{construction_status}' for schedule_run_id={self.schedule_run_id} job_run_id={self.job_run_id} (ignored if duplicate)"
        )

    async def building_type(self, building_type, session=None):
        if not building_type:
            return
        async with self._session(session) as s:
            await insert_ignore(
                s, models.BuildingType, self._add_base_fields({"name": building_type}), ["name"]
            )
        self.logger.info(
            f"[DATA_INGESTION] Inserted BuildingType '{building_type}' for schedule_run_id={self.schedule_run_id} job_run_id={self.job_run_id} (ignored if duplicate)"
        )

    async def building_material(self, building_material, session=None):
        if not building_material:
            return
        async with self._session(session) as s:
            await insert_ignore(
                s, models.BuildingMaterial, self._add_base_fields({"name": building_material}), ["name"]
            )
        self.logger.info(
            f"[DATA_INGESTION] Inserted BuildingMaterial '{building_material}' for schedule_run_id={self.schedule_run_id} job_run_id={self.job_run_id} (ignored if duplicate)"
        )

    async def heating_type(self, heating_type, session=None):
        if not heating_type:
            return
        async with self._session(session) as s:
            await insert_ignore(
                s, models.HeatingType, self._add_base_fields({"name": heating_type}), ["name"]
            )
        self.logger.info(
            f"[DATA_INGESTION] Inserted HeatingType '{heating_type}' for schedule_run_id={self.schedule_run_id} job_run_id={self.job_run_id} (ignored if duplicate)"
        )

    async def ownership_type(self, ownership_form, session=None):
        if not ownership_form:
            return
        async with self._session(session) as s:
            await insert_ignore(
                s, models.OwnershipType, self._add_base_fields({"name": ownership_form}), ["name"]
            )
        self.logger.info(
            f"[DATA_INGESTION] Inserted OwnershipType '{ownership_form}' for schedule_run_id={self.schedule_run_id} job_run_id={self.job_run_id} (ignored if duplicate)"
        )

    async def apartment_listing(self, apartment_data, session=None):
        if not apartment_data:
            return
        async with self._session(session) as s:
            await insert_ignore(s, models.ApartmentListing, apartment_data, ["url"])
        self.logger.info(
            f"[DATA_INGESTION] Inserted ApartmentListing for schedule_run_id={self.schedule_run_id} job_run_id={self.job_run_id} (ignored if duplicate)"
        )

    async def apartment_listing_change(self, change_data, session=None):
        if not change_data:
            return
        async with self._session(session) as s:
            await insert_ignore(s, models.ApartmentListingChange, self._add_base_fields(change_data), [])
        self.logger.info(
            f"[DATA_INGESTION] Inserted ApartmentListingChange for schedule_run_id={self.schedule_run_id} job_run_id={self.job_run_id}"
        )
