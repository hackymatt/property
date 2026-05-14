from contextlib import asynccontextmanager
from src import models


class Update:
    def __init__(self, db, logger, schedule_run_id, job_run_id):
        self.db = db
        self.logger = logger
        self.schedule_run_id = schedule_run_id
        self.job_run_id = job_run_id

    @asynccontextmanager
    async def _session(self, session=None):
        if session is not None:
            yield session
        else:
            async with self.db.get_session() as s:
                async with s.begin():
                    yield s

    async def apartment_listing(self, apartment_data, session=None):
        async with self._session(session) as s:
            stmt = (
                models.ApartmentListing.__table__.update()
                .where(models.ApartmentListing.url == apartment_data["url"])
                .values(apartment_data)
            )
            await s.execute(stmt)
        self.logger.info(
            f"[DATA_INGESTION] Updated ApartmentListing for schedule_run_id={self.schedule_run_id} job_run_id={self.job_run_id}"
        )
