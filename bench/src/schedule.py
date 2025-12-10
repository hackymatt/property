from config import (
    RABBITMQ_SCHEDULE_QUEUE,
    RABBITMQ_SCHEDULE_EXCHANGE,
    RABBITMQ_EXCHANGE_TYPE,
    RABBITMQ_ROUTING_KEY,
    STARTUP_RETRIES,
    STARTUP_RETRY_DELAY,
)
from shared.logger import get_logger
from shared.consts import Status
from dataclasses import asdict
from shared.payloads import SchedulePayload, ScheduleJob

logger = get_logger("bench")


class ScheduleService:
    def __init__(self, rabbitmq):
        self.rabbitmq = rabbitmq

    async def run(self):
        await self.rabbitmq.connect_with_retry(
            retries=STARTUP_RETRIES,
            delay=STARTUP_RETRY_DELAY,
            logger=logger,
        )
        await self.rabbitmq.bind_queue_to_exchange(
            queue=RABBITMQ_SCHEDULE_QUEUE,
            exchange=RABBITMQ_SCHEDULE_EXCHANGE,
            routing_key=RABBITMQ_ROUTING_KEY,
            exchange_type=RABBITMQ_EXCHANGE_TYPE,
        )
        logger.info(
            "Bench consumer started; waiting for messages on queue '%s' bound to exchange '%s' with routing_key '%s'",
            RABBITMQ_SCHEDULE_QUEUE,
            RABBITMQ_SCHEDULE_EXCHANGE,
            RABBITMQ_ROUTING_KEY,
        )
        await self.rabbitmq.consume_forever(
            queue=RABBITMQ_SCHEDULE_QUEUE,
            handler=self._handle_message,
            durable=True,
        )

    def _parse_payload(self, payload: dict) -> SchedulePayload:
        jobs_raw = payload.get("jobs", [])
        jobs = [
            job if isinstance(job, ScheduleJob) else ScheduleJob(**job)
            for job in jobs_raw
        ]

        return SchedulePayload(
            schedule_id=payload.get("schedule_id"),
            jobs=jobs,
        )

    async def _handle_message(self, payload: dict, routing_key: str):
        # Extract run_id and status from routing key: schedule.{run_id}.{status}
        parts = routing_key.split(".")
        run_id = parts[1] if len(parts) > 1 else None
        status = parts[2] if len(parts) > 2 else None

        logger.info(
            "[BENCH] Received %s message for run_id=%s: %s",
            status,
            run_id,
            payload,
        )
        schedule_payload = self._parse_payload(payload)

        for job in schedule_payload.jobs:
            logger.info(
                "Processing job source=%s stage=%s url=%s domain=%s",
                job.source,
                job.stage,
                job.url,
                job.domain,
            )
