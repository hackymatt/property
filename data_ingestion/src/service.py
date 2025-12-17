"""Job logger service - consumes job queue and writes JobRunLog rows (async)"""

from src.logger import logger
from config import (
    RABBITMQ_JOB_QUEUE,
    RABBITMQ_JOB_EXCHANGE,
    RABBITMQ_EXCHANGE_TYPE,
    RABBITMQ_JOB_ROUTING_KEY,
    STARTUP_RETRIES,
    STARTUP_RETRY_DELAY,
)
from shared.payloads import AdPayload, LocationPayload, ApartmentPayload, DataPayload
from src.handlers.apartment import ApartmentHandler
from src import models


class Service:
    def __init__(self, db, rabbitmq):
        self.db = db
        self.rabbitmq = rabbitmq
        self.handlers = {
            "apartment": ApartmentHandler,
        }

    async def run(self):
        await self.db.init(retries=STARTUP_RETRIES, delay=STARTUP_RETRY_DELAY)
        # Reflect models from database schema
        await self.db.reflect_models(models.Base)
        models.Location = models.Base.classes.location
        models.AdvertiserType = models.Base.classes.advertiser_type
        models.AdvertiserName = models.Base.classes.advertiser_name
        models.DevelopmentName = models.Base.classes.development_name
        models.MarketType = models.Base.classes.market_type
        models.TransactionType = models.Base.classes.transaction_type
        models.PropertyType = models.Base.classes.property_type
        models.Room = models.Base.classes.room
        models.Floor = models.Base.classes.floor
        models.BuildingFloor = models.Base.classes.building_floor
        models.ConstructionStatus = models.Base.classes.construction_status
        models.BuildingType = models.Base.classes.building_type
        models.BuildingMaterial = models.Base.classes.building_material
        models.HeatingType = models.Base.classes.heating_type
        models.OwnershipType = models.Base.classes.ownership_type
        models.ApartmentListing = models.Base.classes.apartment_listing
        models.ApartmentListingChange = models.Base.classes.apartment_listing_change

        await self.rabbitmq.connect_with_retry(
            retries=STARTUP_RETRIES,
            delay=STARTUP_RETRY_DELAY,
            logger=logger,
        )
        await self.rabbitmq.bind_queue_to_exchange(
            queue=RABBITMQ_JOB_QUEUE,
            exchange=RABBITMQ_JOB_EXCHANGE,
            routing_key=RABBITMQ_JOB_ROUTING_KEY,
            exchange_type=RABBITMQ_EXCHANGE_TYPE,
        )
        logger.info(
            "Job logger started; waiting for messages on queue '%s' bound to exchange '%s' with routing_key '%s'",
            RABBITMQ_JOB_QUEUE,
            RABBITMQ_JOB_EXCHANGE,
            RABBITMQ_JOB_ROUTING_KEY,
        )
        await self.rabbitmq.consume_forever(
            queue=RABBITMQ_JOB_QUEUE,
            handler=self._handle_message,
            durable=True,
        )

    def _parse_payload(self, payload: dict) -> DataPayload:
        # Accepts dict and returns DataPayload instance
        return DataPayload(
            ad=AdPayload(**payload.get("ad")),
            location=LocationPayload(**payload.get("location")),
            property=ApartmentPayload(**payload.get("property")),
        )

    async def _handle_message(self, payload: dict, routing_key: str):
        # Extract schedule_run_id, job_run_id from routing key: data.{schedule_run_id}.{job_run_id}.pending
        parts = routing_key.split(".")
        schedule_run_id = parts[1] if len(parts) > 1 else None
        job_run_id = parts[2] if len(parts) > 2 else None

        logger.info(
            "[DATA_INGESTION] Received data message for schedule_run_id=%s job_run_id=%s: %s",
            schedule_run_id,
            job_run_id,
            payload,
        )
        data_payload = self._parse_payload(payload)

        property_type = data_payload.property.type
        handler_class = self.handlers.get(property_type)
        if not handler_class:
            logger.error(
                "[DATA_INGESTION] No handler found for property type '%s' for schedule_run_id=%s job_run_id=%s",
                property_type,
                schedule_run_id,
                job_run_id,
            )
            return
        handler = handler_class(self.db, schedule_run_id, job_run_id)
        await handler.handle(data_payload)
        logger.info(
            "[DATA_INGESTION] Completed handling data message for schedule_run_id=%s job_run_id=%s",
            schedule_run_id,
            job_run_id,
        )
