import uuid
from datetime import datetime
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from croniter import croniter
from core.models import BaseModel
from core.choices import ExecutionStatus
from job.models import Job


class Schedule(BaseModel):
    name = models.CharField(max_length=255, unique=True, help_text="Schedule name")
    cron = models.CharField(
        max_length=255,
        help_text="Cron expression (e.g., '0 */6 * * *' for every 6 hours)"
    )
    jobs = models.ManyToManyField(Job, related_name='schedules', help_text="Jobs to run on this schedule")
    is_active = models.BooleanField(default=True, help_text="Whether this schedule is active")
    next_run = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Next scheduled run time (calculated from cron)"
    )

    def clean(self):
        """Validate cron expression."""
        super().clean()
        if self.cron:
            try:
                croniter(self.cron, timezone.now())
            except (ValueError, AttributeError) as e:
                raise ValidationError({'cron': f'Invalid cron expression: {str(e)}'})

    def save(self, *args, **kwargs):
        """Calculate next_run when saving."""
        if self.cron:
            try:
                cron = croniter(self.cron, timezone.now())
                self.next_run = cron.get_next(datetime)
            except (ValueError, AttributeError):
                # Invalid cron expression, keep existing next_run
                pass
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.cron})"

    class Meta:
        db_table = 'schedule'
        ordering = ['name']
        verbose_name_plural = "Schedules"


class ScheduleLog(BaseModel):
    run_id = models.UUIDField(default=uuid.uuid4, editable=False, db_index=True, help_text="Unique identifier for this schedule run")
    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE, related_name='logs')
    status = models.CharField(max_length=20, choices=ExecutionStatus.CHOICES, default=ExecutionStatus.PENDING)
    metadata = models.JSONField(default=dict, blank=True, help_text="Additional metadata about execution (jobs_run, errors, etc.)")

    def __str__(self):
        return f"{self.schedule} - {self.run_id} - {self.status} - {self.created_at}"

    class Meta:
        db_table = 'schedulelog'
        ordering = ['-created_at']
        verbose_name = "Schedule Log"
        verbose_name_plural = "Schedule Logs"

