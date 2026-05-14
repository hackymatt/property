from django.contrib import admin
from .models import ScraperSource


@admin.register(ScraperSource)
class ScraperSourceAdmin(admin.ModelAdmin):
    list_display = ["name", "domain", "is_active", "created_at", "updated_at"]
    list_filter = ["is_active", "domain"]
    search_fields = ["name"]
    readonly_fields = ["created_at", "updated_at"]
    fieldsets = [
        (None, {
            "fields": ["name", "domain", "offer_url_prefix", "is_active", "notes"],
        }),
        ("Preamble (shared helpers)", {
            "fields": ["preamble_code"],
            "classes": ["collapse"],
            "description": (
                "Executed before every snippet. Define imports, site-specific fetch helpers, etc. "
                "Available: fetch (async), deep_get, get_first, all Payload classes."
            ),
        }),
        ("list_pages snippet", {
            "fields": ["list_pages_code"],
            "classes": ["collapse"],
            "description": "Return List[str] of page URLs.",
        }),
        ("list_items snippet", {
            "fields": ["list_items_code"],
            "classes": ["collapse"],
            "description": "Return List[str] of item URLs.",
        }),
        ("get_item snippet", {
            "fields": ["get_item_code"],
            "classes": ["collapse"],
            "description": "Return a DataPayload instance.",
        }),
    ]
