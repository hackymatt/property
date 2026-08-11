from django.contrib import admin
from .models import ScraperSource, ScraperSourceStage


class ScraperSourceStageInline(admin.TabularInline):
    model = ScraperSourceStage
    extra = 1
    fields = ["order", "stage_name", "code_ref"]
    ordering = ["order"]


@admin.register(ScraperSource)
class ScraperSourceAdmin(admin.ModelAdmin):
    list_display = ["name", "domain", "source_kind", "property_type", "is_active", "updated_at"]
    list_filter = ["is_active", "source_kind", "property_type", "domain"]
    search_fields = ["name"]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [ScraperSourceStageInline]
    fieldsets = [
        (None, {
            "fields": [
                "name", "domain", "source_kind", "property_type",
                "offer_url_prefix", "is_active", "notes",
            ],
        }),
        ("Config", {
            "fields": ["config"],
            "description": (
                "Source-level settings, available to every stage. "
                'RCN: {"layer": "transakcje_lokale"} — one source per layer.'
            ),
        }),
        ("Timestamps", {
            "fields": ["created_at", "updated_at"],
            "classes": ["collapse"],
        }),
    ]
