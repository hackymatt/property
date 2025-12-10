from django.db import models
from django.core.exceptions import ValidationError
from core.models import BaseModel
from core.choices import JobSource, JobStage, ExecutionStatus
from domain.models import Domain


class Job(BaseModel):
    domain = models.ForeignKey(Domain, on_delete=models.CASCADE, related_name='jobs')
    source = models.CharField(max_length=255, choices=JobSource.CHOICES)
    stage = models.CharField(max_length=20, choices=JobStage.CHOICES)
    url = models.URLField()
    is_active = models.BooleanField(default=True, help_text="Whether this job is active")

    def clean(self):
        """Validate URL is not empty."""
        super().clean()
        if not self.url:
            raise ValidationError({'url': 'URL is required.'})

    def save(self, *args, **kwargs):
        """Validate before saving."""
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.source} - {self.stage} ({self.domain.name})"

    class Meta:
        ordering = ['-created_at']


class JobLog(BaseModel):
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='logs')
    status = models.CharField(max_length=20, choices=ExecutionStatus.CHOICES, default=ExecutionStatus.PENDING)
    metadata = models.JSONField(default=dict, blank=True, help_text="Additional metadata about execution")

    def __str__(self):
        return f"{self.job} - {self.status} - {self.created_at}"

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Job Log"
        verbose_name_plural = "Job Logs"
