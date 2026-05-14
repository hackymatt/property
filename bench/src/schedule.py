import uuid
from config import (
    RABBITMQ_SCHEDULE_QUEUE,
    RABBITMQ_SCHEDULE_EXCHANGE,
    RABBITMQ_JOB_EXCHANGE,
    RABBITMQ_EXCHANGE_TYPE,
    RABBITMQ_ROUTING_KEY,
    STARTUP_RETRIES,
    STARTUP_RETRY_DELAY,
)
from shared.logger import get_logger
from shared.consts import Status
from shared.payloads import SchedulePayload, JobPayload

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
        return SchedulePayload.model_validate(payload)

    async def _handle_message(self, payload: dict, routing_key: str):
        # Extract schedule_run_id and status from routing key: schedule.{schedule_run_id}.{status}
        parts = routing_key.split(".")
        schedule_run_id = parts[1] if len(parts) > 1 else None
        status = parts[2] if len(parts) > 2 else None

        logger.info(
            "[BENCH] Received %s message for schedule_run_id=%s: %s",
            status,
            schedule_run_id,
            payload,
        )
        schedule_payload = self._parse_payload(payload)

        # Publish schedule running status
        routing_key_running = f"schedule.{schedule_run_id}.{Status.RUNNING}"
        await self.rabbitmq.publish_to_exchange(
            exchange=RABBITMQ_SCHEDULE_EXCHANGE,
            routing_key=routing_key_running,
            message=schedule_payload.model_dump(),
            exchange_type=RABBITMQ_EXCHANGE_TYPE,
        )
        logger.info(
            "[BENCH] Published RUNNING status for schedule_run_id=%s schedule_id=%s",
            schedule_run_id,
            schedule_payload.schedule_id,
        )

        # Publish individual jobs to job exchange
        for job in schedule_payload.jobs:
            job_run_id = str(uuid.uuid4())
            job_routing_key = f"job.{schedule_run_id}.{job_run_id}.pending"
            await self.rabbitmq.publish_to_exchange(
                exchange=RABBITMQ_JOB_EXCHANGE,
                routing_key=job_routing_key,
                message=job.model_dump(),
                exchange_type=RABBITMQ_EXCHANGE_TYPE,
            )
            logger.info(
                "[BENCH] Published job schedule_run_id=%s job_run_id=%s source=%s stage=%s url=%s",
                schedule_run_id,
                job_run_id,
                job.source,
                job.stage,
                job.url,
            )
