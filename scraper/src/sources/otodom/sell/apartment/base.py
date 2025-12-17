from src.sources.otodom.sell.base import OtodomSellBase
from shared.payloads import AdPayload, LocationPayload, ApartmentPayload, DataPayload


class OtodomSellApartmentBase(OtodomSellBase):
    async def list_pages(self, url):
        data = await super().list_pages(url)
        total_pages = data["props"]["pageProps"]["data"]["searchAds"]["pagination"][
            "totalPages"
        ]
        return [f"{url}&page={i}" for i in range(1, total_pages + 1)]

    async def list_items(self, url: str):
        data = await super().list_items(url)
        items = data["props"]["pageProps"]["data"]["searchAds"]["items"]
        return [f"{self.OFFER_URL_PREFIX}{item['slug']}" for item in items]

    async def get_item(self, url):
        data = await super().get_item(url)

        def deep_get(dct, keys, default=None):
            for key in keys:
                if isinstance(dct, dict):
                    dct = dct.get(key, default)
                else:
                    return default
            return dct

        def get_first(lst):
            return lst[0] if isinstance(lst, list) and lst else None

        ad_data = deep_get(data, ["props", "pageProps", "ad"], {})
        location_data = deep_get(ad_data, ["location"], {})
        address_data = deep_get(location_data, ["address"], {})
        coordinates = deep_get(location_data, ["coordinates"], {})
        target = deep_get(ad_data, ["target"], {})
        owner = deep_get(ad_data, ["owner"], {})
        agency = deep_get(ad_data, ["agency"], {}) or {}

        ad = AdPayload(
            created_at=ad_data.get("createdAt"),
            updated_at=ad_data.get("modifiedAt"),
            development_name=ad_data.get("developmentTitle"),
            advertiser_type=owner.get("type"),
            advertiser_name=agency.get("name") if isinstance(agency, dict) else None,
            url=url,
            market_type=target.get("MarketType"),
            transaction_type="sell",
        )

        location = LocationPayload(
            city=deep_get(address_data, ["city", "name"]),
            district=deep_get(address_data, ["district", "name"]),
            subdistrict=deep_get(address_data, ["subdistrict", "name"]),
            municipality=deep_get(address_data, ["municipality", "name"]),
            county=deep_get(address_data, ["county", "name"]),
            postal_code=deep_get(address_data, ["postalCode", "name"]),
            province=deep_get(address_data, ["province", "name"]),
            street=deep_get(address_data, ["street", "name"]),
            latitude=coordinates.get("latitude"),
            longitude=coordinates.get("longitude"),
        )

        property = ApartmentPayload(
            type="apartment",
            area=target.get("Area"),
            price=target.get("Price"),
            price_per_m=target.get("Price_per_m"),
            rooms_num=get_first(target.get("Rooms_num")),
            floor_no=get_first(target.get("Floor_no")),
            building_floors_num=target.get("Building_floors_num"),
            build_year=int(target.get("Build_year")),
            construction_status=get_first(target.get("Construction_status")),
            building_type=get_first(target.get("Building_type")),
            building_material=get_first(target.get("Building_material")),
            heating_type=get_first(target.get("Heating")),
            ownership_type=get_first(target.get("Building_ownership")),
            rent=target.get("Rent"),
        )

        return DataPayload(ad=ad, location=location, property=property)
