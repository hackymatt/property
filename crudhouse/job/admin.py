from django.contrib import admin
from .models import Job, JobRunLog


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ("source", "stage", "domain", "is_active", "created_at")
    list_filter = ("stage", "source", "domain", "is_active", "created_at")
    search_fields = ("source", "url", "domain__name")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        ("Job Info", {"fields": ("domain", "source", "stage", "url", "is_active")}),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )


@admin.register(JobRunLog)
class JobRunLogAdmin(admin.ModelAdmin):
    list_display = (
        "job_run_id",
        "schedule_run_id",
        "parent_job_run_id",
        "source",
        "stage",
        "domain_name",
        "status",
        "created_at",
    )
    list_filter = ("status", "created_at", "source", "stage", "domain_name")
    search_fields = ("job_run_id", "schedule_run_id", "parent_job_run_id", "source", "url", "domain_name")
    readonly_fields = (
        "job_run_id",
        "schedule_run_id",
        "parent_job_run_id",
        "created_at",
        "updated_at",
    )
    fieldsets = (
        (
            "Run Info",
            {
                "fields": (
                    "job_run_id",
                    "schedule_run_id",
                    "parent_job_run_id",
                    "status",
                )
            },
        ),
        ("Job Details", {"fields": ("source", "stage", "url", "domain_name")}),
        ("Metadata", {"fields": ("metadata",)}),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )
