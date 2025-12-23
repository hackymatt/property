from src.registry import SourceRegistry
from src.logger import logger
from shared.payloads import JobPayload


async def scrape(params: JobPayload, throttle_helper) -> dict:
    """Perform scraping

    Args:
        params: Params object with source, stage, and url
        throttle_helper: ThrottleHelper for per-request throttling in Browser

    Returns:
        Dictionary with scraping results
    """
    try:
        logger.info(f"Starting scrape: {params.source} - {params.stage}")

        # Get source class
        source_cls = SourceRegistry.get(params.source)
        if not source_cls:
            logger.error(f"Source not found: {params.source}")
            raise Exception("Source not found")

        # Create source instance with throttle_helper for per-request throttling
        source = source_cls(domain=params.domain_name, throttle_helper=throttle_helper)

        # Get method
        method = getattr(source, params.stage, None)
        if method is None:
            logger.error(f"Method '{params.stage}' not found on {params.source}")
            raise Exception(f"Method '{params.stage}' not found")

        # Call method
        logger.info(f"Calling method: {params.stage}")
        result = await method(params.url)
        logger.info(
            f"Method returned {len(result) if isinstance(result, list) else 1} items"
        )

        return result

    except Exception as e:
        logger.error(f"Scraping error: {e}", exc_info=True)
        raise e
