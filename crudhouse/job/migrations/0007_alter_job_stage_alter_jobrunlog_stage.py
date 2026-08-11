from django.db import migrations, models


class Migration(migrations.Migration):
    """Stage is no longer a closed, global choices set — the stage vocabulary
    now varies per ScraperSource.source_kind and is validated against
    ScraperSourceStage.stage_name at the application layer instead."""

    dependencies = [
        ("job", "0006_job_name"),
    ]

    operations = [
        migrations.AlterField(
            model_name="job",
            name="stage",
            field=models.CharField(
                max_length=100,
                help_text=(
                    "Must match a ScraperSourceStage.stage_name for this source. Not "
                    "choices-restricted here — the stage vocabulary varies per "
                    "ScraperSource.source_kind, see scraper_source app."
                ),
            ),
        ),
        migrations.AlterField(
            model_name="jobrunlog",
            name="stage",
            field=models.CharField(
                max_length=100,
                help_text=(
                    "Must match a ScraperSourceStage.stage_name for this source. Not "
                    "choices-restricted here — the stage vocabulary varies per "
                    "ScraperSource.source_kind, see scraper_source app."
                ),
            ),
        ),
    ]
