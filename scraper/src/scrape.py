from src.dynamic_scraper import DynamicScraper
from src.source_loader import SourceLoader
from src.logger import logger
from shared.payloads import JobPayload


async def scrape(params: JobPayload, throttle_helper, source_loader: SourceLoader):
    logger.info("[scrape] Starting %s — %s", params.source, params.stage)

    config = await source_loader.get(params.source)
    if config is None:
        raise ValueError(f"Source '{params.source}' not found in database — add it via Django admin")

    scraper = DynamicScraper(config, throttle_helper)

    method = getattr(scraper, params.stage, None)
    if method is None:
        raise ValueError(f"Unknown stage '{params.stage}'")

    result = await method(params.url)
    logger.info(
        "[scrape] %s returned %s item(s)",
        params.stage,
        len(result) if isinstance(result, list) else 1,
    )
    return result
