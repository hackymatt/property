from dataclasses import asdict

from config import RABBITMQ_DATA_EXCHANGE, RABBITMQ_EXCHANGE_TYPE
from shared.payloads import DataExchangePayload, JobPayload
from src.logger import logger
from src.sdk.request import Request
from src.source_loader import SourceLoader
from src.stage_registry import resolve
from src.stages.base import RawItem, StageContext


async def scrape(
    params: JobPayload,
    throttle_helper,
    source_loader: SourceLoader,
    rabbitmq,
    schedule_run_id: str | None = None,
    job_run_id: str | None = None,
):
    logger.info("[scrape] Starting %s — %s (code_ref=%s)", params.source, params.stage, params.code_ref)

    config = await source_loader.get(params.source)
    if config is None:
        raise ValueError(f"Source '{params.source}' not found in database — add it via Django admin")

    stage = resolve(params.code_ref)

    async def fetch(url, method="GET", **kwargs):
        async with Request(throttle_helper=throttle_helper) as req:
            if method.upper() == "POST":
                return await req.post(url, domain=config.domain_name, **kwargs)
            return await req.get(url, domain=config.domain_name, **kwargs)

    emitted = 0

    async def emit(item: RawItem):
        """One record -> one data_exchange message, published as it is read.

        The final stage publishes here rather than returning records for
        bench to forward: returning them would put the whole batch into a
        single status message and into JobRunLog.metadata.
        """
        nonlocal emitted
        payload = DataExchangePayload(
            source=params.source,
            job_run_id=job_run_id,
            external_ref=item.external_ref,
            data=item.data,
            property_type=item.property_type or config.property_type,
        )
        await rabbitmq.publish_to_exchange(
            exchange=RABBITMQ_DATA_EXCHANGE,
            routing_key=f"data.{schedule_run_id}.{job_run_id}.pending",
            message=payload.model_dump(),
            exchange_type=RABBITMQ_EXCHANGE_TYPE,
        )
        emitted += 1

    ctx = StageContext(
        url=params.url,
        domain_name=config.domain_name,
        offer_url_prefix=config.offer_url_prefix,
        fetch=fetch,
        emit=emit,
        throttle_helper=throttle_helper,
        source_config=config.config or {},
        params=params.params or {},
        metadata=params.metadata or {},
    )

    result = await stage.run(ctx) or []
    logger.info(
        "[scrape] %s -> %d ref(s) for next stage, %d record(s) emitted",
        params.stage, len(result), emitted,
    )
    return [asdict(ref) if hasattr(ref, "url") and not isinstance(ref, str) else ref for ref in result]
