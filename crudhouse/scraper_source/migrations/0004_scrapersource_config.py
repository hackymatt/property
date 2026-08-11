from django.db import migrations, models


class Migration(migrations.Migration):
    """Source-level settings shared by all of a source's jobs. Job.params is
    per-run scope (which TERYT codes); this is what the source *is* (which
    GPKG layer), so it belongs on the source, not repeated in every job."""

    dependencies = [
        ("scraper_source", "0003_source_kind_and_stage_registry"),
    ]

    operations = [
        migrations.AddField(
            model_name="scrapersource",
            name="config",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text=(
                    "Source-level settings shared by all its jobs, available to every stage. "
                    'RCN example: {"layer": "transakcje_lokale"} — one source per GPKG layer, '
                    "since layers have different columns and map to different property types."
                ),
            ),
        ),
    ]
