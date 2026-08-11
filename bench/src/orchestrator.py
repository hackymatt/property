"""Bench: the stateless stage orchestrator.

Two independent, concurrent responsibilities, both pure message routing —
no domain logic beyond "what stage comes next":

1. Schedule fan-out: a SchedulePayload arrives from scheduler (source+stage+
   url per job, no code_ref) -> resolve each job's code_ref via
   ScraperSourceStage and publish it to job_exchange.
2. Stage advancement: a job's SUCCESS status arrives from scraper (result
   attached in metadata) -> look up the next ScraperSourceStage for that
   source; if there is one, publish a follow-up job per ref in the result;
   if not (this was the last stage), forward each result record to
   data_exchange for data-ingestion to land in PropertyRaw.

Bench holds no in-memory state between messages — every message carries
everything needed (or looks it up fresh from the DB), so any number of
bench replicas can consume the same queues interchangeably."""

import uuid

from config import (
    RABBITMQ_EXCHANGE_TYPE,
    RABBITMQ_JOB_EXCHANGE,
    RABBITMQ_JOB_STATUS_QUEUE,
    RABBITMQ_JOB_STATUS_ROUTING_KEY,
    RABBITMQ_SCHEDULE_EXCHANGE,
    RABBITMQ_SCHEDULE_QUEUE,
    RABBITMQ_SCHEDULE_ROUTING_KEY,
)
from shared.consts import Status
from shared.payloads import JobPayload, SchedulePayload
from src.logger import logger
from src.stage_repository import StageRepository, StageRow


class OrchestratorService:
    def __init__(self, rabbitmq, db):
        self.rabbitmq = rabbitmq
        self.stage_repository = StageRepository(db)

    async def run_schedule_consumer(self):
        await self.rabbitmq.bind_queue_to_exchange(
            queue=RABBITMQ_SCHEDULE_QUEUE,
            exchange=RABBITMQ_SCHEDULE_EXCHANGE,
            routing_key=RABBITMQ_SCHEDULE_ROUTING_KEY,
            exchange_type=RABBITMQ_EXCHANGE_TYPE,
        )
        logger.info(
            "[bench] Schedule consumer bound: queue='%s' exchange='%s' routing_key='%s'",
            RABBITMQ_SCHEDULE_QUEUE, RABBITMQ_SCHEDULE_EXCHANGE, RABBITMQ_SCHEDULE_ROUTING_KEY,
        )
        await self.rabbitmq.consume_forever(
            queue=RABBITMQ_SCHEDULE_QUEUE, handler=self._handle_schedule_message, durable=True,
        )

    async def run_job_status_consumer(self):
        await self.rabbitmq.bind_queue_to_exchange(
            queue=RABBITMQ_JOB_STATUS_QUEUE,
            exchange=RABBITMQ_JOB_EXCHANGE,
            routing_key=RABBITMQ_JOB_STATUS_ROUTING_KEY,
            exchange_type=RABBITMQ_EXCHANGE_TYPE,
        )
        logger.info(
            "[bench] Job status consumer bound: queue='%s' exchange='%s' routing_key='%s'",
            RABBITMQ_JOB_STATUS_QUEUE, RABBITMQ_JOB_EXCHANGE, RABBITMQ_JOB_STATUS_ROUTING_KEY,
        )
        await self.rabbitmq.consume_forever(
            queue=RABBITMQ_JOB_STATUS_QUEUE, handler=self._handle_job_status_message, durable=True,
        )

    # === Schedule fan-out ===

    async def _handle_schedule_message(self, payload: dict, routing_key: str):
        parts = routing_key.split(".")
        schedule_run_id = parts[1] if len(parts) > 1 else None
        status = parts[2] if len(parts) > 2 else None

        logger.info("[bench] Received %s schedule message schedule_run_id=%s: %s", status, schedule_run_id, payload)
        schedule_payload = SchedulePayload.model_validate(payload)

        await self.rabbitmq.publish_to_exchange(
            exchange=RABBITMQ_SCHEDULE_EXCHANGE,
            routing_key=f"schedule.{schedule_run_id}.{Status.RUNNING}",
            message=schedule_payload.model_dump(),
            exchange_type=RABBITMQ_EXCHANGE_TYPE,
        )

        for job in schedule_payload.jobs:
            stage = await self.stage_repository.get_stage(job.source, job.stage)
            if stage is None:
                logger.error(
                    "[bench] Cannot start job — no ScraperSourceStage for source=%s stage=%s",
                    job.source, job.stage,
                )
                continue
            await self._publish_job(
                schedule_run_id, job.source, stage, job.url, job.domain_name, params=job.params,
            )

    # === Stage advancement ===

    async def _handle_job_status_message(self, payload: dict, routing_key: str):
        parts = routing_key.split(".")
        schedule_run_id = parts[1] if len(parts) > 1 else None
        job_run_id = parts[2] if len(parts) > 2 else None
        status = parts[3] if len(parts) > 3 else None

        if status == Status.SUCCESS_NO_CHANGE:
            logger.info(
                "[bench] job_run_id=%s reported no change — stopping (no follow-up)", job_run_id,
            )
            return
        if status != Status.SUCCESS:
            return  # pending/running/failed/retriable_error — nothing to advance

        job_payload = JobPayload.model_validate(payload)
        result = (job_payload.metadata or {}).get("result") or []

        current_stage = await self.stage_repository.get_stage(job_payload.source, job_payload.stage)
        next_stage = await self.stage_repository.get_next_stage(job_payload.source, job_payload.stage)

        if next_stage is None:
            # Final stage: it published its records to data_exchange itself,
            # one message each, as it read them (see scraper's ctx.emit).
            # Nothing to fan out here.
            return

        # The hash-gate only applies leaving the FIRST stage (discovery).
        # Applying it on every hop would be wrong: once one layer's LOAD
        # records the fingerprint, sibling layers of the same file would be
        # gated out mid-pipeline and silently dropped.
        gate_enabled = current_stage is not None and current_stage.order == 1

        for ref in result:
            normalized = self._normalize_ref(ref)
            if normalized is None:
                logger.warning("[bench] Skipping malformed next-stage ref: %r", ref)
                continue
            url, metadata = normalized

            # Generic change-detection: any first-stage ref carrying both
            # file_id + fingerprint gets checked against the last successful
            # LOAD (RCN's DISCOVER -> DOWNLOAD hop today; keyed off the
            # metadata shape, not a source name, so any future
            # FILE_REGISTRY source gets the same behavior for free).
            if gate_enabled and "file_id" in metadata and "fingerprint" in metadata:
                already_done = await self.stage_repository.is_fingerprint_completed(
                    job_payload.source, metadata["file_id"], metadata["fingerprint"],
                )
                if already_done:
                    logger.info(
                        "[bench] file_id=%s already ingested with this fingerprint — skipping %s",
                        metadata["file_id"], next_stage.stage_name,
                    )
                    continue

            await self._publish_job(
                schedule_run_id, job_payload.source, next_stage, url, job_payload.domain_name,
                parent_job_run_id=job_run_id, metadata=metadata, params=job_payload.params,
            )

    @staticmethod
    def _normalize_ref(ref):
        if isinstance(ref, str):
            return ref, {}
        if isinstance(ref, dict) and isinstance(ref.get("url"), str):
            return ref["url"], ref.get("metadata") or {}
        return None

    async def _publish_job(
        self, schedule_run_id, source, stage: StageRow, url, domain_name,
        parent_job_run_id=None, metadata=None, params=None,
    ):
        new_job_run_id = str(uuid.uuid4())
        job_payload = JobPayload(
            source=source,
            stage=stage.stage_name,
            url=url,
            domain_name=domain_name,
            code_ref=stage.code_ref,
            parent_job_run_id=parent_job_run_id,
            # params stay constant for the whole run; metadata is per-hop state
            params=params or None,
            metadata=metadata or None,
        )
        await self.rabbitmq.publish_to_exchange(
            exchange=RABBITMQ_JOB_EXCHANGE,
            routing_key=f"job.{schedule_run_id}.{new_job_run_id}.pending",
            message=job_payload.model_dump(),
            exchange_type=RABBITMQ_EXCHANGE_TYPE,
        )
        logger.info(
            "[bench] Published job schedule_run_id=%s job_run_id=%s source=%s stage=%s url=%s",
            schedule_run_id, new_job_run_id, source, stage.stage_name, url,
        )
