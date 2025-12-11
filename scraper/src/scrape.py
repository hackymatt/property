from src.registry import SourceRegistry
from src.logger import logger
from shared.payloads import JobPayload


async def scrape(params: JobPayload) -> dict:
    """Perform scraping

    Args:
        params: Params object with source, stage, and url

    Returns:
        Dictionary with scraping results
    """
    try:
        logger.info(f"Starting scrape: {params.source} - {params.stage}")

        # Get source class
        source_cls = SourceRegistry.get(params.source)
        if not source_cls:
            logger.error(f"Source not found: {params.source}")
            return {"status": "error", "error": "Source not found"}

        # Create source instance
        source = source_cls()

        # Get method
        method = getattr(source, params.stage, None)
        if method is None:
            logger.error(f"Method '{params.stage}' not found on {params.source}")
            return {
                "status": "error",
                "error": f"Method '{params.stage}' not found",
            }

        # Call method
        logger.info(f"Calling method: {params.stage}")
        result = await method(params.url)
        logger.info(
            f"Method returned {len(result) if isinstance(result, list) else 1} items"
        )

    except Exception as e:
        logger.error(f"Scraping error: {e}", exc_info=True)
        return {"status": "error", "error": str(e)}
