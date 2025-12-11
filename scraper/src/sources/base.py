# sources/base.py
class Base:
    def __init__(self, domain, throttle_helper):
        """Initialize source with domain and throttle_helper for per-request throttling"""
        self.domain = domain
        self.throttle_helper = throttle_helper

    async def list_pages(self, url: str):
        """List all pagination URLs

        Returns:
            list[str]: List of page URLs to scrape
        """
        raise NotImplementedError

    async def list_items(self, url: str):
        """List all item URLs from a page

        Returns:
            list[str]: List of item detail URLs to scrape
        """
        raise NotImplementedError

    async def get_item(self, url: str):
        """Get item details from a detail page

        Returns:
            dict: Item data (no follow-up jobs created)
        """
        raise NotImplementedError
