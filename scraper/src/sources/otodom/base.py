from src.sources.base import Base
from src.sdk.browser import Browser
from src.throttle import DomainThrottle


class OtodomBase(Base):
    throttle = DomainThrottle(max_requests_per_second=1.0, max_requests_per_24h=10000)

    async def list_pages(self, url: str):
        async with Browser(throttle=self.throttle) as browser:
            await browser.goto(url, wait_until="domcontentloaded")
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
