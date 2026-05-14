from django.db import models
from core.models import BaseModel
from domain.models import Domain


class ScraperSource(BaseModel):
    """Defines how to scrape any website via three user-defined code snippets.

    All snippets are executed as async Python function bodies. Each must end
    with a `return` statement.

    Available in every snippet:
        url (str)            — the URL being processed
        fetch (async)        — async fetch(url, method='GET', **kwargs) -> {status, text, headers, url}
        OFFER_URL_PREFIX     — configured base URL for item links
        deep_get(dct, keys)  — safe nested dict accessor
        get_first(lst)       — returns lst[0] or None
        AdPayload, LocationPayload, ApartmentPayload, DataPayload — payload constructors

    Preamble is executed first and its globals (imports, helpers) are available in all three snippets.
    """

    name = models.CharField(
        max_length=255,
        unique=True,
        help_text="Unique identifier used in Job.source, e.g. 'otodom/sell/apartment/owner'",
    )
    domain = models.ForeignKey(Domain, on_delete=models.CASCADE, related_name="scraper_sources")
    offer_url_prefix = models.CharField(
        max_length=500,
        blank=True,
        help_text="Base URL for item links, available as OFFER_URL_PREFIX in snippets",
    )
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    preamble_code = models.TextField(
        blank=True,
        help_text=(
            "Shared code run before each snippet. Define site-specific helpers here, e.g.:\n"
            "  import re, json, html as html_module\n"
            "  async def get_next_data(url):\n"
            "      resp = await fetch(url, headers={...})\n"
            "      ..."
        ),
    )
    list_pages_code = models.TextField(
        help_text="Return List[str] of page URLs. Use fetch to retrieve the page and preamble helpers to parse it."
    )
    list_items_code = models.TextField(
        help_text="Return List[str] of item URLs. Use fetch, OFFER_URL_PREFIX, and preamble helpers."
    )
    get_item_code = models.TextField(
        help_text="Return a DataPayload instance. Use fetch, payload constructors, and preamble helpers."
    )

    class Meta:
        db_table = "scraper_source"
        ordering = ["name"]

    def __str__(self):
        return self.name
