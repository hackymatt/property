from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from core.models import BaseModel


class Domain(BaseModel):
    name = models.CharField(max_length=255, unique=True, help_text="Domain name (e.g., otodom.pl, facebook.com)")
    is_active = models.BooleanField(default=True, help_text="Whether this domain is actively being scraped")
    
    # Throttling configuration
    requests_per_second = models.FloatField(
        default=1.0,
        validators=[MinValueValidator(0.1), MaxValueValidator(100)],
        help_text="Maximum requests per second (e.g., 0.5 = 1 request every 2 seconds)"
    )
    delay_between_requests = models.FloatField(
        default=1.0,
        validators=[MinValueValidator(0.1), MaxValueValidator(300)],
        help_text="Delay in seconds between requests"
    )
    concurrent_requests = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(50)],
        help_text="Number of concurrent requests allowed"
    )
    
    # Retry configuration
    max_retries = models.PositiveIntegerField(
        default=3,
        validators=[MinValueValidator(0), MaxValueValidator(10)],
        help_text="Maximum number of retries for failed requests"
    )
    retry_delay = models.FloatField(
        default=5.0,
        validators=[MinValueValidator(1), MaxValueValidator(300)],
        help_text="Delay in seconds before retrying"
    )
    
    # Timeout configuration
    timeout = models.PositiveIntegerField(
        default=30,
        validators=[MinValueValidator(5), MaxValueValidator(300)],
        help_text="Request timeout in seconds"
    )
    
    # Rate limiting
    requests_per_hour = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Maximum requests per hour (None = unlimited)"
    )
    
    notes = models.TextField(blank=True, help_text="Additional notes or comments")

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'domain'
        ordering = ['name']
        verbose_name_plural = "Domains"

