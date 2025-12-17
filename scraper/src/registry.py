from src.sources.otodom.sell.apartment.owner import OtodomSellApartmentOwner
from src.sources.otodom.sell.apartment.agency import OtodomSellApartmentAgency
from src.sources.otodom.sell.apartment.developer import OtodomSellApartmentDeveloper
from shared.consts import Source


class SourceRegistry:
    _sources = {
        Source.OTODOM_SELL_APARTMENT_OWNER: OtodomSellApartmentOwner,
        Source.OTODOM_SELL_APARTMENT_AGENCY: OtodomSellApartmentAgency,
        Source.OTODOM_SELL_APARTMENT_DEVELOPER: OtodomSellApartmentDeveloper,
    }

    @classmethod
    def get(cls, name: str):
        return cls._sources.get(name)

    @classmethod
    def list(cls):
        return list(cls._sources.keys())
