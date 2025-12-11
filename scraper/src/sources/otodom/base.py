from urllib.parse import urlparse

from src.sources.base import Base
from src.sdk.browser import Browser


class OtodomBase(Base):
    async def list_pages(self, url: str):
        async with Browser(
            throttle_helper=self.throttle_helper, headless=True
        ) as browser:
            await browser.goto(url, domain=self.domain, wait_until="domcontentloaded")
            await browser.page.wait_for_selector(
                'ul[data-cy="nexus-pagination-component"]', timeout=60000
            )

            last_page_button = await browser.query_selector_all(
                'ul[data-cy="nexus-pagination-component"] button.css-k2c6vi'
            )
            last_page = 1
            if len(last_page_button):
                last_page_text = await browser.inner_text(last_page_button[-1])
                last_page = int(last_page_text.strip())

            return [f"{url}?page={i}" for i in range(1, last_page + 1)]

    async def list_items(self, url: str):
        raise NotImplementedError
