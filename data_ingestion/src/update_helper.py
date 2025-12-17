from src.db_utils import insert_ignore
from src import models
from datetime import datetime, timezone


class Update:
    def __init__(self, db, logger, schedule_run_id, job_run_id):
        self.db = db
        self.logger = logger
        self.schedule_run_id = schedule_run_id
        self.job_run_id = job_run_id

    async def apartment_listing(self, apartment_data):
        async with self.db.get_session() as session:
            stmt = (
                models.ApartmentListing.__table__.update()
                .where(models.ApartmentListing.url == apartment_data["url"])
                .values(apartment_data)
            )
            await session.execute(stmt)
            await session.commit()
        self.logger.info(
            f"[DATA_INGESTION] Updated ApartmentListing for schedule_run_id={self.schedule_run_id} job_run_id={self.job_run_id}"
        )
