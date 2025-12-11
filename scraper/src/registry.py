from src.sources.otodom.sale.apartment.owner import OtodomSaleApartmentOwner
from shared.consts import Source


class SourceRegistry:
    _sources = {Source.OTODOM_SALE_APARTMENT_OWNER: OtodomSaleApartmentOwner}

    @classmethod
    def get(cls, name: str):
        return cls._sources.get(name)

    @classmethod
    def list(cls):
        return list(cls._sources.keys())
