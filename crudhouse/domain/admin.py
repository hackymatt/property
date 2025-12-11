from django.contrib import admin
from .models import Domain


@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "is_active",
        "requests_per_second",
        "burst_capacity",
        "created_at",
    )
    list_filter = ("is_active", "created_at")
    search_fields = ("name",)
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        ("Basic Info", {"fields": ("name", "is_active")}),
        (
            "Throttling",
            {
                "fields": (
                    "requests_per_second",
                    "burst_capacity",
                    "concurrent_requests",
                )
            },
        ),
        ("Retry", {"fields": ("max_retries", "retry_delay")}),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )
