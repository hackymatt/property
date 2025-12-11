# sources/base.py
class Base:
    async def list_pages(self, url: str):
        raise NotImplementedError

    async def list_items(self, url: str):
        raise NotImplementedError
