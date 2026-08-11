from django.db import models

from core.choices import PropertyType
from core.models import OptionalRunIdField
from scraper_source.models import ScraperSource


class PropertyRaw(models.Model):
    """Insert-only landing/history log for every source (Otodom, RCN, ...).

    One row per distinct observed content_hash for a given (source,
    external_ref) — not a snapshot-per-crawl. Idempotency is enforced by the
    unique constraint below combined with INSERT ... ON CONFLICT DO NOTHING
    in data-ingestion; rows are never updated or deleted by the application.

    Note: no GIN index on `json` and no PARTITION BY RANGE on `partition_date`
    yet — both are Postgres-only and this project still supports a sqlite
    fallback for local dev without DATABASE=postgres. Add both once the
    project runs exclusively on Postgres and volume justifies it.
    """

    property_type = models.CharField(max_length=20, choices=PropertyType.CHOICES)
    source = models.ForeignKey(ScraperSource, on_delete=models.PROTECT, related_name="raw_records")
    external_ref = models.CharField(
        max_length=2048,
        help_text="Natural key from the source: URL (portal) or record_hash (RCN, per transaction record).",
    )
    content_hash = models.CharField(max_length=64, help_text="hash(json) — sha256 hex digest.")
    json = models.JSONField(help_text="Structured payload produced by the source's last stage.")
    job_run_id = OptionalRunIdField(help_text="JobRunLog.job_run_id that produced this row.")
    partition_date = models.DateField(db_index=True, help_text="date(created_at), for future range partitioning.")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "property_raw"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["source", "external_ref", "content_hash"],
                name="uniq_source_external_ref_content_hash",
            ),
        ]
        indexes = [
            models.Index(fields=["source", "external_ref", "-created_at"], name="idx_property_raw_latest"),
        ]

    def __str__(self):
        return f"{self.source_id}:{self.external_ref} @ {self.created_at}"
