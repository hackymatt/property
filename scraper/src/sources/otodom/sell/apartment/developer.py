from src.sources.otodom.sell.apartment.base import OtodomSellApartmentBase
from src.sources.otodom.base import OtodomBase
from src.sdk.request import Request


class OtodomSellApartmentDeveloper(OtodomSellApartmentBase):
    INVESTMENT_UNIT_QUERY = """query InvestmentUnit($id: Int64!, $lookup: AdvertsLookupInput!) {\n  paginatedUnits: paginatedDevelopmentUnits(developmentId: $id, lookup: $lookup) {\n    __typename\n    ...PaginatedInvestmentUnitsFragment\n  }\n}\nfragment PaginatedInvestmentUnitsFragment on AdvertsPages {\n  items {\n    id\n    title\n    url\n    target\n    adCategory {\n      name\n      __typename\n    }\n    characteristics {\n      key\n      value\n      currency\n      localizedValue\n      __typename\n    }\n    images {\n      small\n      __typename\n    }\n    location {\n      coordinates {\n        latitude\n        longitude\n        radius\n        zoomLevel\n        __typename\n      }\n      __typename\n    }\n    category {\n      id\n      name {\n        locale\n        value\n        __typename\n      }\n      __typename\n    }\n    owner: legacyOwner {\n      id\n      name\n      type\n      phones\n      imageUrl\n      contacts {\n        name\n        phone\n        imageURLSmall\n        __typename\n      }\n      __typename\n    }\n    createdAt\n    specialOffer {\n      details {\n        startDate\n        endDate\n        ... on InvestmentSpecialOffer {\n          appliesToAllUnits\n          __typename\n        }\n        __typename\n      }\n      ... on PriceDiscount {\n        discountValue\n        minPriceLastDays\n        __typename\n      }\n      __typename\n    }\n    floorPlans\n    __typename\n  }\n  isPriceHidden\n  pagination {\n    totalResults: total_results\n    totalPages: total_pages\n    page\n    __typename\n  }\n  facets {\n    numberOfRooms\n    floorNumber\n    price\n    area\n    numberOfRoomsWithCounter\n    __typename\n  }\n  __typename\n}"""

    async def _fetch_investment_unit_urls(self, ids):
        api_url = "https://www.otodom.pl/api/query"
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
        }
        results = []
        # Use the domain for throttling (extracted from the URL)
        async with Request(self.throttle_helper) as requester:
            for item_id in ids:
                payload = {
                    "operationName": "InvestmentUnit",
                    "query": self.INVESTMENT_UNIT_QUERY,
                    "variables": {
                        "id": item_id,
                        "lookup": {
                            "filters": {"numberOfRooms": []},
                            "page": 1,
                            "pageSize": 10000,
                            "sort": {"by": "Price", "direction": "asc"},
                            "withFacets": False,
                        },
                    },
                }
                response = await requester.post(
                    api_url, json=payload, headers=headers, domain=self.domain
                )
                response.raise_for_status()
                item_data = response.json()
                unit_items = item_data["data"]["paginatedUnits"]["items"]
                urls = [unit["url"] for unit in unit_items]
                results.extend(urls)
        return results

    async def list_items(self, url: str):
        data = await OtodomBase.list_items(self, url)
        items = data["props"]["pageProps"]["data"]["searchAds"]["items"]
        ids = [item["id"] for item in items]
        return await self._fetch_investment_unit_urls(ids)
