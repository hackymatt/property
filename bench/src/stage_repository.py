"""Read-only lookups against ScraperSourceStage — the DB-driven registry of
which stages a ScraperSource runs through, and in what order. This is the
only place bench needs domain knowledge: everything else is generic
message routing."""

import json
from dataclasses import dataclass
from typing import Optional

from sqlalchemy import select, text

from src import models
from src.logger import logger


@dataclass
class StageRow:
    stage_name: str
    order: int
    code_ref: str


class StageRepository:
    def __init__(self, db):
        self.db = db

    async def get_stage(self, source_name: str, stage_name: str) -> Optional[StageRow]:
        """Look up a specific stage by name — used when fanning out the
        first job of a source's pipeline (its stage_name is already known,
        e.g. from Job.stage), to resolve its code_ref."""
        async with self.db.get_session() as session:
            row = (
                await session.execute(
                    select(models.ScraperSourceStage)
                    .join(models.ScraperSource, models.ScraperSourceStage.source_id == models.ScraperSource.id)
                    .where(
                        models.ScraperSource.name == source_name,
                        models.ScraperSourceStage.stage_name == stage_name,
                    )
                )
            ).scalar_one_or_none()

        if row is None:
            logger.warning("[StageRepository] No stage '%s' registered for source '%s'", stage_name, source_name)
            return None
        return StageRow(stage_name=row.stage_name, order=row.order, code_ref=row.code_ref)

    async def get_next_stage(self, source_name: str, current_stage_name: str) -> Optional[StageRow]:
        """Returns the stage after current_stage_name for this source, or
        None if current_stage_name is the last one (or unknown)."""
        current = await self.get_stage(source_name, current_stage_name)
        if current is None:
            return None

        async with self.db.get_session() as session:
            row = (
                await session.execute(
                    select(models.ScraperSourceStage)
                    .join(models.ScraperSource, models.ScraperSourceStage.source_id == models.ScraperSource.id)
                    .where(
                        models.ScraperSource.name == source_name,
                        models.ScraperSourceStage.order == current.order + 1,
                    )
                )
            ).scalar_one_or_none()

        if row is None:
            return None
        return StageRow(stage_name=row.stage_name, order=row.order, code_ref=row.code_ref)

    async def get_final_stage(self, source_name: str) -> Optional[StageRow]:
        async with self.db.get_session() as session:
            row = (
                await session.execute(
                    select(models.ScraperSourceStage)
                    .join(models.ScraperSource, models.ScraperSourceStage.source_id == models.ScraperSource.id)
                    .where(models.ScraperSource.name == source_name)
                    .order_by(models.ScraperSourceStage.order.desc())
                    .limit(1)
                )
            ).scalar_one_or_none()

        if row is None:
            return None
        return StageRow(stage_name=row.stage_name, order=row.order, code_ref=row.code_ref)

    async def is_fingerprint_completed(self, source_name: str, file_id: str, fingerprint: dict) -> bool:
        """Change-detection for file-registry sources: has THIS exact
        fingerprint already been ingested end to end?

        Keys off the source's own final stage (looked up, never hardcoded —
        stage names are per-source configuration) and requires at least one
        success with no failure for the same fingerprint. The final stage
        runs once per batch, so "one success" alone would wrongly mark a
        partially-failed file as done and leave permanent gaps.

        Raw SQL because the filter is on JSONB fields of a reflected table,
        where automap gives no typed operators to build this cleanly.
        """
        final_stage = await self.get_final_stage(source_name)
        if final_stage is None:
            logger.warning("[StageRepository] Source '%s' has no stages registered", source_name)
            return False

        query = text(
            """
            SELECT status, count(*) AS n
            FROM jobrunlog
            WHERE source = :source
              AND stage = :stage
              AND status IN ('success', 'failed')
              AND metadata ->> 'file_id' = :file_id
              AND metadata -> 'fingerprint' = CAST(:fingerprint AS jsonb)
            GROUP BY status
            """
        )

        async with self.db.get_session() as session:
            rows = (
                await session.execute(
                    query,
                    {
                        "source": source_name,
                        "stage": final_stage.stage_name,
                        "file_id": file_id,
                        "fingerprint": json.dumps(fingerprint, sort_keys=True),
                    },
                )
            ).all()

        counts = {status: n for status, n in rows}
        return counts.get("success", 0) > 0 and counts.get("failed", 0) == 0
