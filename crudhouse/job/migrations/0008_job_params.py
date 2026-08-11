from django.db import migrations, models


class Migration(migrations.Migration):
    """Per-job parameters for the first stage. Portal sources express their
    scope in `url`; file-registry sources (RCN) have no single fetchable URL,
    so their scope (which TERYT codes to check) needs its own channel."""

    dependencies = [
        ("job", "0007_alter_job_stage_alter_jobrunlog_stage"),
    ]

    operations = [
        migrations.AddField(
            model_name="job",
            name="params",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text=(
                    "Source-specific parameters for this job, passed to the first stage. "
                    "Portal sources usually need none (the scope is the url). "
                    'RCN example — one county: {"teryt_codes": ["1261"]}, all: {"teryt_codes": "all"}.'
                ),
            ),
        ),
    ]
