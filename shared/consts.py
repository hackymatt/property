"""Shared status choices used by multiple services."""


class Status:
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    SUCCESS_NO_CHANGE = "success_no_change"
    RETRIABLE_ERROR = "retriable_error"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Stage:
    """Known stage-name string constants, used to avoid magic literals in
    bench/scraper code. NOT an enforced/exhaustive set — the authoritative
    stage sequence for a given ScraperSource lives in ScraperSourceStage
    (crudhouse DB), keyed by these same string values."""

    # PORTAL_LISTING (e.g. Otodom)
    LIST_PAGES = "list_pages"
    LIST_ITEMS = "list_items"
    GET_ITEM = "get_item"

    # FILE_REGISTRY (e.g. RCN)
    DISCOVER = "discover"
    DOWNLOAD = "download"
    EXTRACT = "extract"
    TRANSFORM = "transform"
    LOAD = "load"


class SourceKind:
    PORTAL_LISTING = "PORTAL_LISTING"
    FILE_REGISTRY = "FILE_REGISTRY"


class PropertyType:
    APARTMENT = "APARTMENT"
    HOUSE = "HOUSE"
    LAND = "LAND"
    COMMERCIAL = "COMMERCIAL"


class Source:
    OTODOM_SELL_APARTMENT_OWNER = "otodom/sell/apartment/owner"
    OTODOM_SELL_APARTMENT_AGENCY = "otodom/sell/apartment/agency"
    OTODOM_SELL_APARTMENT_DEVELOPER = "otodom/sell/apartment/developer"
