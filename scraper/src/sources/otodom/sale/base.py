from src.sources.otodom.base import OtodomBase


class OtodomSaleBase(OtodomBase):
    async def list_items(self, url: str):
        raise NotImplementedError
