from contextlib import asynccontextmanager
from sqlalchemy import select as sa_select
from src import models


class Select:
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
                yield s

    async def apartment(self, url, session=None):
        async with self._session(session) as s:
            result = await s.scalars(
                sa_select(models.ApartmentListing).where(models.ApartmentListing.url == url)
            )
            apartment = result.first()
        if apartment:
            self.logger.info(
                f"[DATA_INGESTION] Retrieved ApartmentListing for schedule_run_id={self.schedule_run_id} job_run_id={self.job_run_id}"
            )
        return apartment
