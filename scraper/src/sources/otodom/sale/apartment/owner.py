from src.sources.otodom.sale.apartment.base import OtodomSaleApartmentBase
from src.sdk.browser import Browser


class OtodomSaleApartmentOwner(OtodomSaleApartmentBase):
    async def list_items(self, url: str):
        async with Browser(
            throttle_helper=self.throttle_helper, headless=True
        ) as browser:
            await browser.goto(url, domain=self.domain, wait_until="networkidle")
            await browser.page.wait_for_selector(
                'div[data-cy="search.listing.organic"]'
            )

            # Find all listing items on the page
            listing_items = await browser.query_selector_all(
                'div[data-cy="search.listing.organic"] li article[data-sentry-component="AdvertCard"] a[data-cy="listing-item-link"]'
            )

            items = []
            for item in listing_items:
                href = await item.get_attribute("href")
                if href:
                    # Convert relative URLs to absolute
                    if href.startswith("/"):
                        href = f"https://www.otodom.pl{href}"
                    items.append(href)

            return items
