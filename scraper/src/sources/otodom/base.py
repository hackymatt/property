from src.sources.base import Base
from src.sdk.request import Request

import json
import re
import html as html_module
from json import JSONDecodeError

from src.logger import logger


class OtodomBase(Base):
    OFFER_URL_PREFIX = "https://www.otodom.pl/pl/oferta/"

    async def _get_data_from_page(self, url: str):
        async with Request(throttle_helper=self.throttle_helper) as requester:
            resp = await requester.get(
                url,
                headers={
                    "Accept": "text/html,application/xhtml+xml",
                    "User-Agent": "Mozilla/5.0",
                    "Accept-Encoding": "gzip, deflate, br",
                },
                domain=self.domain,
            )

            html = resp["text"]

            m = re.search(
                r'<script[^>]+id="__NEXT_DATA__"[^>]*>(.*?)</script>',
                html,
                re.S,
            )

            if not m:
                m = re.search(
                    r"<script[^>]*>\s*window\.__NEXT_DATA__\s*=\s*(\{.*?\})\s*;?\s*</script>",
                    html,
                    re.S,
                )

            if not m:
                logger.error(f"__NEXT_DATA__ not found on {url}")
                raise RuntimeError(f"__NEXT_DATA__ not found on {url}")

            data = html_module.unescape(m.group(1).strip())

            try:
                return json.loads(data)
            except JSONDecodeError:
                cleaned = re.sub(r";\s*$", "", data)
                cleaned = re.sub(r"^\s*window\.__NEXT_DATA__\s*=\s*", "", cleaned)
                return json.loads(cleaned)

    async def list_pages(self, url: str):
        return await self._get_data_from_page(url)

    async def list_items(self, url: str):
        return await self._get_data_from_page(url)

    async def get_item(self, url: str):
        return await self._get_data_from_page(url)
