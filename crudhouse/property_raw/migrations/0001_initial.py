import django.db.models.deletion
from django.db import migrations, models

import core.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("scraper_source", "0003_source_kind_and_stage_registry"),
    ]

    operations = [
        migrations.CreateModel(
            name="PropertyRaw",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "property_type",
                    models.CharField(
                        choices=[
                            ("APARTMENT", "Apartment"),
                            ("HOUSE", "House"),
                            ("LAND", "Land"),
                            ("COMMERCIAL", "Commercial"),
                        ],
                        max_length=20,
                    ),
                ),
                (
                    "external_ref",
                    models.CharField(
                        help_text="Natural key from the source: URL (portal) or record_hash (RCN, per transaction record).",
                        max_length=2048,
                    ),
                ),
                (
                    "content_hash",
                    models.CharField(help_text="hash(json) — sha256 hex digest.", max_length=64),
                ),
                (
                    "json",
                    models.JSONField(help_text="Structured payload produced by the source's last stage."),
                ),
                (
                    "job_run_id",
                    core.models.OptionalRunIdField(
                        blank=True,
                        db_index=True,
                        help_text="JobRunLog.job_run_id that produced this row.",
                        null=True,
                    ),
                ),
                (
                    "partition_date",
                    models.DateField(db_index=True, help_text="date(created_at), for future range partitioning."),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "source",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="raw_records",
                        to="scraper_source.scrapersource",
                    ),
                ),
            ],
            options={
                "db_table": "property_raw",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="propertyraw",
            index=models.Index(fields=["source", "external_ref", "-created_at"], name="idx_property_raw_latest"),
        ),
        migrations.AddConstraint(
            model_name="propertyraw",
            constraint=models.UniqueConstraint(
                fields=("source", "external_ref", "content_hash"),
                name="uniq_source_external_ref_content_hash",
            ),
        ),
    ]
