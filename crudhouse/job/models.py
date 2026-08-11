from django.db import models
from django.core.exceptions import ValidationError
from core.models import (
    BaseModel,
    LogBaseModel,
    RunIdField,
    OptionalRunIdField,
    DomainNameField,
)
from domain.models import Domain


class JobFieldsMixin(models.Model):
    """Mixin containing common fields shared between Job and JobRunLog."""

    source = models.CharField(
        max_length=255,
        help_text="Must match a ScraperSource name, e.g. 'otodom/sell/apartment/owner'",
    )
    stage = models.CharField(
        max_length=100,
        help_text=(
            "Must match a ScraperSourceStage.stage_name for this source. Not "
            "choices-restricted here — the stage vocabulary varies per "
            "ScraperSource.source_kind, see scraper_source app."
        ),
    )
    url = models.URLField()

    class Meta:
        abstract = True


class Job(JobFieldsMixin, BaseModel):
    name = models.CharField(max_length=255, unique=True)
    domain = models.ForeignKey(Domain, on_delete=models.CASCADE, related_name="jobs")
    params = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "Source-specific parameters for this job, passed to the first stage. "
            "Portal sources usually need none (the scope is the url). "
            'RCN example — one county: {"teryt_codes": ["1261"]}, all: {"teryt_codes": "all"}.'
        ),
    )
    is_active = models.BooleanField(
        default=True, help_text="Whether this job is active"
    )

    def clean(self):
        """Validate URL is not empty."""
        super().clean()
        if not self.url:
            raise ValidationError({"url": "URL is required."})

    def save(self, *args, **kwargs):
        """Validate before saving."""
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.source} - {self.stage} ({self.domain.name})"

    class Meta:
        db_table = "job"
        ordering = ["-created_at"]


class JobRunLog(JobFieldsMixin, LogBaseModel):
    domain_name = DomainNameField()
    parent_job_run_id = OptionalRunIdField(
        help_text="UUID of the parent job run (if this is a follow-up job)",
    )
    job_run_id = RunIdField(
        help_text="Unique identifier for this job run",
    )

    def __str__(self):
        return f"{self.source} - {self.stage} ({self.domain_name}) - {self.status} - {self.created_at}"

    class Meta:
        db_table = "jobrunlog"
        ordering = ["-created_at"]
        verbose_name = "Job Run Log"
        verbose_name_plural = "Job Run Logs"
