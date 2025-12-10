"""Shared status choices used by multiple services."""


class Status:
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Stage:
    LIST_PAGES = "list_pages"
    LIST_ITEMS = "list_items"
    GET_ITEM = "get_item"


class Source:
    OTODOM_SALE_APARTMENT_OWNER = "otodom/sale/apartment/owner"
