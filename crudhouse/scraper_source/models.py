from django.db import models
from core.choices import PropertyType, SourceKind
from core.models import BaseModel
from domain.models import Domain


class ScraperSource(BaseModel):
    """Configuration for a scrapable/ingestible source (a portal search, or a
    file registry like RCN). Holds no executable code — the handler logic for
    each of its stages lives as a versioned Python class in the `scraper`
    service repo (see ScraperSourceStage.code_ref)."""

    name = models.CharField(
        max_length=255,
        unique=True,
        help_text="Unique identifier used in Job.source, e.g. 'otodom/sell/apartment/owner'",
    )
    domain = models.ForeignKey(Domain, on_delete=models.CASCADE, related_name="scraper_sources")
    source_kind = models.CharField(
        max_length=20,
        choices=SourceKind.CHOICES,
        help_text="Determines which stage vocabulary applies (see ScraperSourceStage).",
    )
    property_type = models.CharField(
        max_length=20,
        choices=PropertyType.CHOICES,
        help_text="Default PropertyRaw.property_type for records produced by this source.",
    )
    offer_url_prefix = models.CharField(
        max_length=500,
        blank=True,
        help_text="Base URL for item links (PORTAL_LISTING sources only).",
    )
    config = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "Source-level settings shared by all its jobs, available to every stage. "
            'RCN example: {"layer": "transakcje_lokale"} — one source per GPKG layer, '
            "since layers have different columns and map to different property types."
        ),
    )
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "scraper_source"
        ordering = ["name"]

    def __str__(self):
        return self.name


class ScraperSourceStage(BaseModel):
    """Ordered registry of the stages a ScraperSource runs through. Holds no
    code — `code_ref` points to a Stage class registered in the `scraper`
    service's STAGE_REGISTRY (e.g. "otodom.ListPagesStage")."""

    source = models.ForeignKey(ScraperSource, on_delete=models.CASCADE, related_name="stages")
    stage_name = models.CharField(
        max_length=100,
        help_text="e.g. 'list_pages', 'discover' — must match shared.consts.Stage values.",
    )
    order = models.PositiveIntegerField(help_text="Execution order within this source, starting at 1.")
    code_ref = models.CharField(
        max_length=255,
        help_text="Dotted reference to the Stage class in the scraper repo's STAGE_REGISTRY, e.g. 'otodom.ListPagesStage'.",
    )

    class Meta:
        db_table = "scraper_source_stage"
        ordering = ["source", "order"]
        constraints = [
            models.UniqueConstraint(fields=["source", "stage_name"], name="uniq_source_stage_name"),
            models.UniqueConstraint(fields=["source", "order"], name="uniq_source_stage_order"),
        ]

    def __str__(self):
        return f"{self.source.name} [{self.order}] {self.stage_name}"
