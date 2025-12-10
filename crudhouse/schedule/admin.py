from django.contrib import admin
from django.core.exceptions import ValidationError
from .models import Schedule, ScheduleLog


@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ('name', 'cron', 'is_active', 'next_run', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'cron')
    readonly_fields = ('created_at', 'updated_at', 'next_run')
    filter_horizontal = ('jobs',)
    fieldsets = (
        ('Schedule Info', {
            'fields': ('name', 'cron', 'is_active')
        }),
        ('Execution', {
            'fields': ('next_run',)
        }),
        ('Jobs', {
            'fields': ('jobs',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def save_related(self, request, form, formsets, change):
        """Save M2M relationships and validate at least one job is assigned."""
        super().save_related(request, form, formsets, change)
        if not form.instance.jobs.exists():
            from django.contrib import messages
            messages.error(request, "Schedule must have at least one job assigned.")
            # Delete the object since it's invalid
            form.instance.delete()
            raise ValidationError("Schedule must have at least one job assigned.")


@admin.register(ScheduleLog)
class ScheduleLogAdmin(admin.ModelAdmin):
    list_display = ('schedule', 'status', 'created_at')
    list_filter = ('status', 'created_at', 'schedule__name')
    search_fields = ('schedule__name', 'metadata')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Schedule Info', {
            'fields': ('schedule', 'status')
        }),
        ('Metadata', {
            'fields': ('metadata',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
