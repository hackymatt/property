"""Otodom (PORTAL_LISTING) stage classes: LIST_PAGES -> LIST_ITEMS -> GET_ITEM.

Ported from the equivalent, independently-implemented pipeline at
data-hub/pipelines/otodom/{discovery/discovery.py, extract/stages/fetcher.py}
(plain HTTP + regex/__NEXT_DATA__ parsing, no browser needed) — NOT copied
1:1 from the previous DB-stored ScraperSource snippets, whose exact text
lived only in the (unavailable, non-versioned) database. See ADR-1 / plan
v6 checkpoint for context.

Otodom's search and listing pages are Next.js pages that ship their full
payload inline as a <script id="__NEXT_DATA__"> JSON blob, so plain HTTP
GETs are enough — no headless browser required (src/sdk/browser.py stays
available, unused, for a future source that genuinely needs one).
"""

import hashlib
import json
import re
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from src.logger import logger
from src.sdk.binary import throttled_get_bytes
from src.sdk.storage import get_storage
from src.stages.base import NextStageRef, RawItem, Stage, StageContext

DEFAULT_PHOTO_SIZE = "large"


def _sanitize(value: str) -> str:
    """Keep folder names safe and predictable across local disk and S3."""
    cleaned = re.sub(r"[^A-Za-z0-9._/-]+", "-", value).strip("-/")
    return cleaned or "unknown"


def _host(url: str) -> str:
    return urlparse(url).netloc or "unknown"

NEXT_DATA_RE = re.compile(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.DOTALL)
JSON_LD_RE = re.compile(r'<script type="application/ld\+json"[^>]*>(.*?)</script>', re.DOTALL)
OFFER_URL_RE = re.compile(r'href="(/pl/oferta/[^"?#]+)"')
JSON_LD_TYPES = {"Product", "RealEstateListing", "Residence", "Apartment", "House"}

PAGE_SIZE = 72
# Safety cap so a mis-detected total_pages can't turn one job into thousands
# of follow-up fetches. Override per source via config["max_pages"] — Kraków
# apartments-for-sale alone is ~182 pages, so a bigger city will exceed this.
MAX_PAGES = 200

# Candidate JSON key paths under props.pageProps — Otodom can rename these
# between deploys, so every extractor here tries several and degrades to
# "logs a warning, returns empty" rather than raising on a shape mismatch.
LISTINGS_PATHS = (
    ("data", "searchAds", "items"),
    ("searchAds", "items"),
    ("listings", "items"),
    ("data", "items"),
)
TOTAL_PAGES_PATHS = (
    ("data", "searchAds", "pagination", "totalPages"),
    ("searchAds", "pagination", "totalPages"),
)
AD_PATHS = (
    ("ad",),
    ("adOffer",),
    ("offer",),
    ("data", "ad"),
    ("data", "offer"),
)


def _dig(d: dict, *keys):
    for key in keys:
        if not isinstance(d, dict):
            return None
        d = d.get(key)
    return d


def _paginated_url(base_url: str, page: int) -> str:
    parsed = urlparse(base_url)
    query = dict(parse_qsl(parsed.query))
    query.update({"page": str(page), "limit": str(PAGE_SIZE)})
    return urlunparse(parsed._replace(query=urlencode(query)))


def _parse_next_data(html: str) -> dict | None:
    match = NEXT_DATA_RE.search(html)
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError as e:
        logger.warning("[otodom] __NEXT_DATA__ was not valid JSON: %s", e)
        return None


class ListPagesStage(Stage):
    """ctx.url is an Otodom search-results base URL. Returns paginated URLs
    (including page 1) for LIST_ITEMS to process."""

    async def run(self, ctx: StageContext) -> list[str]:
        page_1_url = _paginated_url(ctx.url, 1)
        response = await ctx.fetch(page_1_url)
        pages = [page_1_url]

        if response["status"] != 200:
            logger.warning("[otodom.ListPagesStage] status=%s for %s", response["status"], page_1_url)
            return pages

        data = _parse_next_data(response["text"])
        page_props = _dig(data, "props", "pageProps") if data else None
        total_pages = None
        for path in TOTAL_PAGES_PATHS:
            total_pages = _dig(page_props, *path)
            if total_pages:
                break

        if not total_pages:
            logger.warning(
                "[otodom.ListPagesStage] total_pages not found for %s — "
                "returning page 1 only, inspect __NEXT_DATA__ shape",
                ctx.url,
            )
            return pages

        total_pages = int(total_pages)
        max_pages = int(ctx.source_config.get("max_pages") or MAX_PAGES)

        if total_pages > max_pages:
            # Silent truncation here would look like listings "disappearing",
            # so say it loudly: everything past the cap is simply never seen.
            logger.warning(
                "[otodom.ListPagesStage] %s reports %d pages but max_pages=%d — "
                "SKIPPING %d page(s) (~%d listings). Raise ScraperSource.config['max_pages'] "
                "or split the search into narrower slices.",
                ctx.url, total_pages, max_pages, total_pages - max_pages,
                (total_pages - max_pages) * PAGE_SIZE,
            )

        for page in range(2, min(total_pages, max_pages) + 1):
            pages.append(_paginated_url(ctx.url, page))

        logger.info(
            "[otodom.ListPagesStage] %d page(s) of %d for %s", len(pages), total_pages, ctx.url,
        )
        return pages


class ListItemsStage(Stage):
    """ctx.url is one search-results page URL. Returns item (offer) URLs
    found on it — __NEXT_DATA__ primary, regex-scan fallback unioned in so a
    JSON shape change degrades to 'logs a warning' rather than 0 results."""

    async def run(self, ctx: StageContext) -> list[str]:
        response = await ctx.fetch(ctx.url)
        if response["status"] != 200:
            logger.warning("[otodom.ListItemsStage] status=%s for %s", response["status"], ctx.url)
            return []

        html = response["text"]
        json_urls = self._from_next_data(html)
        regex_urls = self._from_regex(html)

        if not json_urls and regex_urls:
            logger.warning(
                "[otodom.ListItemsStage] __NEXT_DATA__ found 0 items but regex "
                "fallback found %d for %s — JSON schema may have changed",
                len(regex_urls),
                ctx.url,
            )

        return sorted(json_urls | regex_urls)

    @staticmethod
    def _from_next_data(html: str) -> set[str]:
        data = _parse_next_data(html)
        if not data:
            return set()
        page_props = _dig(data, "props", "pageProps") or {}

        items = []
        for path in LISTINGS_PATHS:
            items = _dig(page_props, *path)
            if items:
                break

        urls = set()
        for item in items or []:
            if not isinstance(item, dict):
                continue
            slug = item.get("slug") or item.get("id")
            if slug:
                urls.add(f"https://www.otodom.pl/pl/oferta/{slug}")
        return urls

    @staticmethod
    def _from_regex(html: str) -> set[str]:
        return {f"https://www.otodom.pl{path}" for path in OFFER_URL_RE.findall(html)}


class GetItemStage(Stage):
    """ctx.url is a single offer URL — the final Otodom stage. Emits the
    extracted ad payload as-is (whatever shape Otodom's own JSON has);
    normalization into a canonical schema is deliberately NOT done here —
    PropertyRaw stores it verbatim, mapping happens in a later phase once
    the Property/Listing domain model exists (see plan section 8)."""

    async def run(self, ctx: StageContext) -> list[str]:
        response = await ctx.fetch(ctx.url)
        if response["status"] != 200:
            logger.warning("[otodom.GetItemStage] status=%s for %s", response["status"], ctx.url)
            return []

        html = response["text"]
        ad = self._from_next_data(html) or self._from_json_ld(html)
        if ad is None:
            logger.warning(
                "[otodom.GetItemStage] could not extract listing data for %s "
                "(tried __NEXT_DATA__ and JSON-LD) — page structure may have changed",
                ctx.url,
            )
            return []

        await ctx.emit(RawItem(external_ref=ctx.url, data=ad))

        # Hand the photo URLs to the next stage, if the source has one. When
        # it doesn't, bench treats this as the final stage and simply drops
        # the ref — so photo downloading stays opt-in per source.
        image_urls = self._image_urls(ad, ctx.source_config.get("photo_size", DEFAULT_PHOTO_SIZE))
        if not image_urls:
            return []

        return [
            NextStageRef(
                url=ctx.url,
                metadata={"listing_id": self._listing_id(ad, ctx.url), "image_urls": image_urls},
            )
        ]

    @staticmethod
    def _listing_id(ad: dict, url: str) -> str:
        """Folder name for this listing's photos. Prefers the ad's own slug/
        id; falls back to a hash of the URL so a missing field can never
        collapse two listings into one folder."""
        for key in ("slug", "publicId", "id"):
            value = ad.get(key)
            if value:
                return _sanitize(str(value))
        return hashlib.sha256(url.encode()).hexdigest()[:16]

    @staticmethod
    def _from_next_data(html: str) -> dict | None:
        data = _parse_next_data(html)
        if not data:
            return None
        page_props = _dig(data, "props", "pageProps") or {}
        for path in AD_PATHS:
            ad = _dig(page_props, *path)
            if isinstance(ad, dict) and ad:
                return ad
        return None

    @staticmethod
    def _from_json_ld(html: str) -> dict | None:
        for raw in JSON_LD_RE.findall(html):
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError:
                continue
            candidates = obj if isinstance(obj, list) else [obj]
            for candidate in candidates:
                if isinstance(candidate, dict) and candidate.get("@type") in JSON_LD_TYPES:
                    return candidate
        return None

    @staticmethod
    def _image_urls(ad: dict, size: str) -> list[str]:
        images = ad.get("images")
        if not isinstance(images, list):
            return []

        urls = []
        for image in images:
            if not isinstance(image, dict):
                continue
            # Fall back through smaller variants so a listing missing the
            # preferred size still yields something rather than nothing.
            for candidate in (size, "large", "medium", "small", "thumbnail"):
                value = image.get(candidate)
                if isinstance(value, str) and value:
                    urls.append(value)
                    break
        return urls


class DownloadPhotosStage(Stage):
    """Downloads a listing's photos into one folder per listing.

    One job per listing (not per photo): a listing's photos belong together
    and the folder is the unit of work, so this keeps message volume at one
    per listing instead of one per image. Individual photo failures are
    logged and skipped — one broken image must not fail the whole listing.

    Idempotent: already-stored photos are skipped via storage.exists(), so
    re-running a listing costs one cheap check per photo, not a re-download.

    Photos come from a CDN host, not the portal's domain, so they are
    throttled under that host — add a Domain row for it to tune the rate,
    otherwise the service's defaults apply."""

    async def run(self, ctx: StageContext) -> list[str]:
        listing_id = ctx.metadata.get("listing_id")
        image_urls = ctx.metadata.get("image_urls") or []
        if not listing_id or not image_urls:
            logger.warning("[otodom.DownloadPhotosStage] nothing to download for %s", ctx.url)
            return []

        storage = get_storage()
        prefix = f"{_sanitize(ctx.source_config.get('photo_prefix') or 'otodom')}/{listing_id}"

        saved = skipped = failed = 0
        for index, url in enumerate(image_urls):
            key = f"{prefix}/{index:03d}-{hashlib.sha256(url.encode()).hexdigest()[:12]}.jpg"
            if storage.exists(key):
                skipped += 1
                continue

            data = await throttled_get_bytes(ctx.throttle_helper, _host(url), url)
            if not data:
                failed += 1
                continue

            storage.save(key, data)
            saved += 1

        logger.info(
            "[otodom.DownloadPhotosStage] listing=%s photos: %d saved, %d already present, %d failed",
            listing_id, saved, skipped, failed,
        )
        return []
