"""Site-agnostic scraper: executes user-defined code snippets for any website."""

import asyncio
import json

from shared.payloads import AdPayload, ApartmentPayload, DataPayload, LocationPayload
from src.source_loader import SourceConfig
from src.sdk.request import Request
from src.logger import logger


# ──────────────────────────────────────────────────────────────────────────────
# Helpers exposed to snippet context
# ──────────────────────────────────────────────────────────────────────────────

def _deep_get(dct, keys, default=None):
    for key in keys:
        if isinstance(dct, dict):
            dct = dct.get(key, default)
        else:
            return default
    return dct


def _get_first(lst):
    return lst[0] if isinstance(lst, list) and lst else None


# ──────────────────────────────────────────────────────────────────────────────
# Snippet execution
# ──────────────────────────────────────────────────────────────────────────────

async def _run_snippet(code: str, globs: dict):
    """Wrap `code` in an async function body, inject `globs` as its globals, and call it.

    The snippet can use `await` freely and must end with `return <value>`.
    All keys in `globs` are accessible as bare names inside the snippet.
    """
    indent = "    "
    wrapped = ["async def _snippet():"] + [f"{indent}{line}" for line in code.splitlines()]
    exec(compile("\n".join(wrapped), "<snippet>", "exec"), globs)  # noqa: S102
    return await globs["_snippet"]()


# ──────────────────────────────────────────────────────────────────────────────
# Scraper
# ──────────────────────────────────────────────────────────────────────────────

class DynamicScraper:
    """Scraper whose full logic — including HTTP fetching — is defined by user snippets.

    The engine only provides throttling and a `fetch` helper. Snippets handle
    everything else: page retrieval, HTML/JSON parsing, and data extraction.
    This makes the scraper completely site-agnostic.

    Execution flow per stage:
        1. Build base context (fetch, helpers, payload classes, OFFER_URL_PREFIX)
        2. Execute preamble_code into the context (defines shared helpers/imports)
        3. Execute the stage snippet inside the enriched context
    """

    def __init__(self, config: SourceConfig, throttle_helper):
        self.config = config
        self.throttle_helper = throttle_helper

    def _make_fetch(self):
        """Return an async fetch(url, method, **kwargs) helper for snippets."""
        throttle_helper = self.throttle_helper
        domain = self.config.domain_name

        async def fetch(url, method="GET", **kwargs):
            async with Request(throttle_helper=throttle_helper) as req:
                if method.upper() == "POST":
                    return await req.post(url, domain=domain, **kwargs)
                return await req.get(url, domain=domain, **kwargs)

        return fetch

    def _build_context(self) -> dict:
        """Base globals available to every snippet (and the preamble)."""
        return {
            "fetch": self._make_fetch(),
            "OFFER_URL_PREFIX": self.config.offer_url_prefix,
            "deep_get": _deep_get,
            "get_first": _get_first,
            "AdPayload": AdPayload,
            "LocationPayload": LocationPayload,
            "ApartmentPayload": ApartmentPayload,
            "DataPayload": DataPayload,
            # Standard library conveniences
            "asyncio": asyncio,
            "json": json,
        }

    async def _runtime(self, extra: dict | None = None) -> dict:
        """Build the full runtime context: base globals + preamble execution."""
        globs = self._build_context()
        if extra:
            globs.update(extra)
        if self.config.preamble_code:
            exec(compile(self.config.preamble_code, "<preamble>", "exec"), globs)  # noqa: S102
        return globs

    async def list_pages(self, url: str) -> list[str]:
        globs = await self._runtime({"url": url})
        result = await _run_snippet(self.config.list_pages_code, globs)
        logger.info("[DynamicScraper] list_pages → %d page(s) from %s", len(result), url)
        return result

    async def list_items(self, url: str) -> list[str]:
        globs = await self._runtime({"url": url})
        result = await _run_snippet(self.config.list_items_code, globs)
        logger.info("[DynamicScraper] list_items → %d item(s) from %s", len(result), url)
        return result

    async def get_item(self, url: str) -> DataPayload:
        globs = await self._runtime({"url": url})
        return await _run_snippet(self.config.get_item_code, globs)
