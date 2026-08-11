from django.contrib import admin

from .models import PropertyRaw


@admin.register(PropertyRaw)
class PropertyRawAdmin(admin.ModelAdmin):
    """Read-only: PropertyRaw is insert-only, written exclusively by data-ingestion."""

    list_display = ["id", "source", "property_type", "external_ref", "created_at"]
    list_filter = ["property_type", "source"]
    search_fields = ["external_ref", "content_hash"]
    readonly_fields = [f.name for f in PropertyRaw._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
