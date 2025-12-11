from src.sources.otodom.sale.base import OtodomSaleBase


class OtodomSaleApartmentBase(OtodomSaleBase):
    async def list_items(self, url: str):
        raise NotImplementedError
