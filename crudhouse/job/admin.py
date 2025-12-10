from django.contrib import admin
from .models import Job, JobLog


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ('source', 'stage', 'domain', 'is_active', 'created_at')
    list_filter = ('stage', 'source', 'domain', 'is_active', 'created_at')
    search_fields = ('source', 'url', 'domain__name')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Job Info', {
            'fields': ('domain', 'source', 'stage', 'url', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(JobLog)
class JobLogAdmin(admin.ModelAdmin):
    list_display = ('job', 'status', 'created_at')
    list_filter = ('status', 'created_at', 'job__source', 'job__stage')
    search_fields = ('job__source', 'metadata')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Job Info', {
            'fields': ('job', 'status')
        }),
        ('Metadata', {
            'fields': ('metadata',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
