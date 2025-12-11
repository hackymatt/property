import uuid
from django.db import models
from core.choices import ExecutionStatus


class RunIdField(models.UUIDField):
    """Custom UUID field for run identifiers with consistent configuration."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("db_index", True)
        kwargs.setdefault("editable", False)
        kwargs.setdefault("default", uuid.uuid4)
        super().__init__(*args, **kwargs)


class OptionalRunIdField(models.UUIDField):
    """Custom UUID field for optional run identifiers (nullable)."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("db_index", True)
        kwargs.setdefault("null", True)
        kwargs.setdefault("blank", True)
        super().__init__(*args, **kwargs)


class DomainNameField(models.CharField):
    """Custom CharField for domain names with consistent configuration."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("max_length", 255)
        kwargs.setdefault("help_text", "Domain name (e.g., otodom.pl, facebook.com)")
        super().__init__(*args, **kwargs)


class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class LogBaseModel(BaseModel):
    """Base model for all log models with common fields."""

    schedule_run_id = RunIdField(help_text="Unique identifier for the schedule run")
    status = models.CharField(
        max_length=20, choices=ExecutionStatus.CHOICES, default=ExecutionStatus.PENDING
    )
    metadata = models.JSONField(
        default=dict, blank=True, help_text="Additional metadata about execution"
    )

    class Meta:
        abstract = True
