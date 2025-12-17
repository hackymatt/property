from src.sources.base import Base
from src.sdk.browser import Browser

import json


class OtodomBase(Base):
    OFFER_URL_PREFIX = "https://www.otodom.pl/pl/oferta/"

    async def _get_data_from_page(self, url: str):
        async with Browser(
            throttle_helper=self.throttle_helper, headless=True
        ) as browser:
            await browser.goto(url, domain=self.domain, wait_until="domcontentloaded")

            data = await browser.page.eval_on_selector(
                "#__NEXT_DATA__", "el => el.textContent"
            )

            return json.loads(data)

    async def list_pages(self, url: str):
        return await self._get_data_from_page(url)

    async def list_items(self, url: str):
        return await self._get_data_from_page(url)

    async def get_item(self, url: str):
        return await self._get_data_from_page(url)
