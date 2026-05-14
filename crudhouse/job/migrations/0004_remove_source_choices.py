from django.db import migrations, models


class Migration(migrations.Migration):
    """Remove hardcoded source choices — sources are now defined in ScraperSource."""

    dependencies = [
        ("job", "0003_alter_job_source_alter_jobrunlog_source"),
    ]

    operations = [
        migrations.AlterField(
            model_name="job",
            name="source",
            field=models.CharField(
                max_length=255,
                help_text="Must match a ScraperSource name, e.g. 'otodom/sell/apartment/owner'",
            ),
        ),
        migrations.AlterField(
            model_name="jobrunlog",
            name="source",
            field=models.CharField(max_length=255),
        ),
    ]
