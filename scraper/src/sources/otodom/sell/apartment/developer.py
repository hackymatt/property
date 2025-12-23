from src.sources.otodom.sell.apartment.base import OtodomSellApartmentBase
from src.sources.otodom.base import OtodomBase
from src.sdk.request import Request
import asyncio
import json
from json import JSONDecodeError

from src.logger import logger


class OtodomSellApartmentDeveloper(OtodomSellApartmentBase):
    INVESTMENT_UNIT_QUERY = """query InvestmentUnit($id: Int64!, $lookup: AdvertsLookupInput!) {\n  paginatedUnits: paginatedDevelopmentUnits(developmentId: $id, lookup: $lookup) {\n    __typename\n    ...PaginatedInvestmentUnitsFragment\n  }\n}\nfragment PaginatedInvestmentUnitsFragment on AdvertsPages {\n  items {\n    id\n    title\n    url\n    target\n    adCategory {\n      name\n      __typename\n    }\n    characteristics {\n      key\n      value\n      currency\n      localizedValue\n      __typename\n    }\n    images {\n      small\n      __typename\n    }\n    location {\n      coordinates {\n        latitude\n        longitude\n        radius\n        zoomLevel\n        __typename\n      }\n      __typename\n    }\n    category {\n      id\n      name {\n        locale\n        value\n        __typename\n      }\n      __typename\n    }\n    owner: legacyOwner {\n      id\n      name\n      type\n      phones\n      imageUrl\n      contacts {\n        name\n        phone\n        imageURLSmall\n        __typename\n      }\n      __typename\n    }\n    createdAt\n    specialOffer {\n      details {\n        startDate\n        endDate\n        ... on InvestmentSpecialOffer {\n          appliesToAllUnits\n          __typename\n        }\n        __typename\n      }\n      ... on PriceDiscount {\n        discountValue\n        minPriceLastDays\n        __typename\n      }\n      __typename\n    }\n    floorPlans\n    __typename\n  }\n  isPriceHidden\n  pagination {\n    totalResults: total_results\n    totalPages: total_pages\n    page\n    __typename\n  }\n  facets {\n    numberOfRooms\n    floorNumber\n    price\n    area\n    numberOfRoomsWithCounter\n    __typename\n  }\n  __typename\n}"""
    API_URL = "https://www.otodom.pl/api/query"

    async def _fetch_investment_unit_urls(self, ids):
        """Fetch unit URLs for all given development ids.

        Uses a small helper to fetch each development (paginated) and runs those
        helpers concurrently to improve throughput while sharing the same
        `Request` session.
        """

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
        }

        if not ids:
            return []

        async def _fetch_units_for_id(requester: Request, item_id: int) -> list:
            """Fetch all paginated unit URLs for a single development id.

            Returns an empty list on recoverable errors (so one bad id doesn't
            stop the whole scrape).
            """
            results: list = []
            page = 1
            page_size = 50

            while True:
                payload = {
                    "operationName": "InvestmentUnit",
                    "query": self.INVESTMENT_UNIT_QUERY,
                    "variables": {
                        "id": item_id,
                        "lookup": {
                            "filters": {"numberOfRooms": []},
                            "page": page,
                            "pageSize": page_size,
                            "sort": {"by": "Price", "direction": "asc"},
                            "withFacets": False,
                        },
                    },
                }

                try:
                    resp = await requester.post(
                        self.API_URL, json=payload, headers=headers, domain=self.domain
                    )
                except Exception:
                    logger.exception(
                        "HTTP error fetching investment units for id=%s page=%s",
                        item_id,
                        page,
                    )
                    return results

                status = resp.get("status", 0)
                if status != 200:
                    logger.warning(
                        "API returned status=%s for id=%s page=%s; skipping id",
                        status,
                        item_id,
                        page,
                    )
                    return results

                try:
                    item_data = json.loads(resp.get("text", ""))
                except JSONDecodeError:
                    logger.exception(
                        "Invalid JSON from investments API for id=%s page=%s",
                        item_id,
                        page,
                    )
                    return results

                paginated_units = (item_data or {}).get("data", {}).get(
                    "paginatedUnits"
                ) or {}
                unit_items = paginated_units.get("items", [])
                if not unit_items:
                    # nothing to add; end pagination
                    return results

                urls = [u.get("url") for u in unit_items if u.get("url")]
                results.extend(urls)

                total_pages = paginated_units.get("pagination", {}).get("totalPages", 1)
                if page >= total_pages:
                    break
                page += 1

            return results

        # Run per-development fetchers concurrently but catch per-task errors
        async with Request(self.throttle_helper) as requester:
            tasks = [_fetch_units_for_id(requester, item_id) for item_id in ids]
            gathered = await asyncio.gather(*tasks, return_exceptions=True)

        results: list = []
        for idx, res in enumerate(gathered):
            item_id = ids[idx]
            if isinstance(res, Exception):
                logger.exception("Fetching units failed for development id=%s", item_id)
                continue
            if res:
                logger.info("Development %s: added %d unit URLs", item_id, len(res))
                results.extend(res)

        return results

    async def list_items(self, url: str):
        data = await OtodomBase.list_items(self, url)
        items = data["props"]["pageProps"]["data"]["searchAds"]["items"]
        flats = [
            f"{self.OFFER_URL_PREFIX}{item['slug']}"
            for item in items
            if item.get("estate") == "FLAT"
        ]
        investments = [
            item["id"] for item in items if item.get("estate") == "INVESTMENT"
        ]
        investments_flats = await self._fetch_investment_unit_urls(investments)

        return [*flats, *investments_flats]
