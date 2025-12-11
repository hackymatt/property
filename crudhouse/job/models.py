from django.db import models
from django.core.exceptions import ValidationError
from core.models import (
    BaseModel,
    LogBaseModel,
    RunIdField,
    OptionalRunIdField,
    DomainNameField,
)
from core.choices import JobSource, JobStage
from domain.models import Domain


class JobFieldsMixin(models.Model):
    """Mixin containing common fields shared between Job and JobRunLog."""

    source = models.CharField(max_length=255, choices=JobSource.CHOICES)
    stage = models.CharField(max_length=20, choices=JobStage.CHOICES)
    url = models.URLField()

    class Meta:
        abstract = True


class Job(JobFieldsMixin, BaseModel):
    domain = models.ForeignKey(Domain, on_delete=models.CASCADE, related_name="jobs")
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
