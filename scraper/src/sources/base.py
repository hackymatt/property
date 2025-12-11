# sources/base.py
class Base:
    def __init__(self, domain, throttle_helper):
        """Initialize source with domain and throttle_helper for per-request throttling"""
        self.domain = domain
        self.throttle_helper = throttle_helper

    async def list_pages(self, url: str):
        raise NotImplementedError

    async def list_items(self, url: str):
        raise NotImplementedError
