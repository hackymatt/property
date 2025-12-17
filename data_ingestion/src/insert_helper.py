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

    async def location(self, location_data):
        if location_data:
            async with self.db.get_session() as session:
                await insert_ignore(
                    session,
                    models.Location,
                    self._add_base_fields(location_data),
                    [
                        "latitude",
                        "longitude",
                    ],
                )
            self.logger.info(
                f"[DATA_INGESTION] Inserted Location for schedule_run_id={self.schedule_run_id} job_run_id={self.job_run_id} (ignored if duplicate)"
            )

    async def advertiser_type(self, advertiser_type):
        if advertiser_type:
            async with self.db.get_session() as session:
                await insert_ignore(
                    session,
                    models.AdvertiserType,
                    self._add_base_fields({"name": advertiser_type}),
                    ["name"],
                )
            self.logger.info(
                f"[DATA_INGESTION] Inserted AdvertiserType '{advertiser_type}' for schedule_run_id={self.schedule_run_id} job_run_id={self.job_run_id} (ignored if duplicate)"
            )

    async def advertiser_name(self, advertiser_name):
        if advertiser_name:
            async with self.db.get_session() as session:
                await insert_ignore(
                    session,
                    models.AdvertiserName,
                    self._add_base_fields({"name": advertiser_name}),
                    ["name"],
                )
            self.logger.info(
                f"[DATA_INGESTION] Inserted AdvertiserName '{advertiser_name}' for schedule_run_id={self.schedule_run_id} job_run_id={self.job_run_id} (ignored if duplicate)"
            )

    async def development_name(self, development_name):
        if development_name:
            async with self.db.get_session() as session:
                await insert_ignore(
                    session,
                    models.DevelopmentName,
                    self._add_base_fields({"name": development_name}),
                    ["name"],
                )
            self.logger.info(
                f"[DATA_INGESTION] Inserted DevelopmentName '{development_name}' for schedule_run_id={self.schedule_run_id} job_run_id={self.job_run_id} (ignored if duplicate)"
            )

    async def market_type(self, market_type):
        if market_type:
            async with self.db.get_session() as session:
                await insert_ignore(
                    session,
                    models.MarketType,
                    self._add_base_fields({"name": market_type}),
                    ["name"],
                )
            self.logger.info(
                f"[DATA_INGESTION] Inserted MarketType '{market_type}' for schedule_run_id={self.schedule_run_id} job_run_id={self.job_run_id} (ignored if duplicate)"
            )

    async def transaction_type(self, transaction_type):
        if transaction_type:
            async with self.db.get_session() as session:
                await insert_ignore(
                    session,
                    models.TransactionType,
                    self._add_base_fields({"name": transaction_type}),
                    ["name"],
                )
            self.logger.info(
                f"[DATA_INGESTION] Inserted TransactionType '{transaction_type}' for schedule_run_id={self.schedule_run_id} job_run_id={self.job_run_id} (ignored if duplicate)"
            )

    async def property_type(self, property_type):
        if property_type:
            async with self.db.get_session() as session:
                await insert_ignore(
                    session,
                    models.PropertyType,
                    self._add_base_fields({"name": property_type}),
                    ["name"],
                )
            self.logger.info(
                f"[DATA_INGESTION] Inserted PropertyType '{property_type}' for schedule_run_id={self.schedule_run_id} job_run_id={self.job_run_id} (ignored if duplicate)"
            )

    async def room(self, rooms_num):
        if rooms_num is not None:
            async with self.db.get_session() as session:
                await insert_ignore(
                    session,
                    models.Room,
                    self._add_base_fields({"name": str(rooms_num)}),
                    ["name"],
                )
            self.logger.info(
                f"[DATA_INGESTION] Inserted Room '{rooms_num}' for schedule_run_id={self.schedule_run_id} job_run_id={self.job_run_id} (ignored if duplicate)"
            )

    async def floor(self, floor_no):
        if floor_no is not None:
            async with self.db.get_session() as session:
                await insert_ignore(
                    session,
                    models.Floor,
                    self._add_base_fields({"name": str(floor_no)}),
                    ["name"],
                )
            self.logger.info(
                f"[DATA_INGESTION] Inserted Floor '{floor_no}' for schedule_run_id={self.schedule_run_id} job_run_id={self.job_run_id} (ignored if duplicate)"
            )

    async def building_floor(self, building_floors_num):
        if building_floors_num is not None:
            async with self.db.get_session() as session:
                await insert_ignore(
                    session,
                    models.BuildingFloor,
                    self._add_base_fields({"name": str(building_floors_num)}),
                    ["name"],
                )
            self.logger.info(
                f"[DATA_INGESTION] Inserted BuildingFloor '{building_floors_num}' for schedule_run_id={self.schedule_run_id} job_run_id={self.job_run_id} (ignored if duplicate)"
            )

    async def construction_status(self, construction_status):
        if construction_status:
            async with self.db.get_session() as session:
                await insert_ignore(
                    session,
                    models.ConstructionStatus,
                    self._add_base_fields({"name": construction_status}),
                    ["name"],
                )
            self.logger.info(
                f"[DATA_INGESTION] Inserted ConstructionStatus '{construction_status}' for schedule_run_id={self.schedule_run_id} job_run_id={self.job_run_id} (ignored if duplicate)"
            )

    async def building_type(self, building_type):
        if building_type:
            async with self.db.get_session() as session:
                await insert_ignore(
                    session,
                    models.BuildingType,
                    self._add_base_fields({"name": building_type}),
                    ["name"],
                )
            self.logger.info(
                f"[DATA_INGESTION] Inserted BuildingType '{building_type}' for schedule_run_id={self.schedule_run_id} job_run_id={self.job_run_id} (ignored if duplicate)"
            )

    async def building_material(self, building_material):
        if building_material:
            async with self.db.get_session() as session:
                await insert_ignore(
                    session,
                    models.BuildingMaterial,
                    self._add_base_fields({"name": building_material}),
                    ["name"],
                )
            self.logger.info(
                f"[DATA_INGESTION] Inserted BuildingMaterial '{building_material}' for schedule_run_id={self.schedule_run_id} job_run_id={self.job_run_id} (ignored if duplicate)"
            )

    async def heating_type(self, heating_type):
        if heating_type:
            async with self.db.get_session() as session:
                await insert_ignore(
                    session,
                    models.HeatingType,
                    self._add_base_fields({"name": heating_type}),
                    ["name"],
                )
            self.logger.info(
                f"[DATA_INGESTION] Inserted HeatingType '{heating_type}' for schedule_run_id={self.schedule_run_id} job_run_id={self.job_run_id} (ignored if duplicate)"
            )

    async def ownership_type(self, ownership_form):
        if ownership_form:
            async with self.db.get_session() as session:
                await insert_ignore(
                    session,
                    models.OwnershipType,
                    self._add_base_fields({"name": ownership_form}),
                    ["name"],
                )
            self.logger.info(
                f"[DATA_INGESTION] Inserted OwnershipType '{ownership_form}' for schedule_run_id={self.schedule_run_id} job_run_id={self.job_run_id} (ignored if duplicate)"
            )

    async def apartment_listing(self, apartment_data):
        if apartment_data:
            async with self.db.get_session() as session:
                await insert_ignore(
                    session,
                    models.ApartmentListing,
                    apartment_data,
                    ["url"],
                )
            self.logger.info(
                f"[DATA_INGESTION] Inserted ApartmentListing '{apartment_data}' for schedule_run_id={self.schedule_run_id} job_run_id={self.job_run_id} (ignored if duplicate)"
            )

    async def apartment_listing_change(self, change_data):
        if change_data:
            async with self.db.get_session() as session:
                await insert_ignore(
                    session,
                    models.ApartmentListingChange,
                    self._add_base_fields(change_data),
                    [],
                )
            self.logger.info(
                f"[DATA_INGESTION] Inserted ApartmentListingChange '{change_data}' for schedule_run_id={self.schedule_run_id} job_run_id={self.job_run_id} (ignored if duplicate)"
            )
