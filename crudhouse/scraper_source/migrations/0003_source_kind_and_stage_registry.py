import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """Replace the four hardcoded code-snippet fields on ScraperSource with
    configuration fields (source_kind/property_type) and a new
    ScraperSourceStage registry table. Stage handler code now lives as
    versioned classes in the scraper service repo, not in the database."""

    dependencies = [
        ("scraper_source", "0002_alter_scrapersource_get_item_code_and_more"),
    ]

    operations = [
        migrations.RemoveField(model_name="scrapersource", name="preamble_code"),
        migrations.RemoveField(model_name="scrapersource", name="list_pages_code"),
        migrations.RemoveField(model_name="scrapersource", name="list_items_code"),
        migrations.RemoveField(model_name="scrapersource", name="get_item_code"),
        migrations.AddField(
            model_name="scrapersource",
            name="source_kind",
            field=models.CharField(
                choices=[("PORTAL_LISTING", "Portal listing"), ("FILE_REGISTRY", "File registry")],
                default="PORTAL_LISTING",
                max_length=20,
                help_text="Determines which stage vocabulary applies (see ScraperSourceStage).",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="scrapersource",
            name="property_type",
            field=models.CharField(
                choices=[
                    ("APARTMENT", "Apartment"),
                    ("HOUSE", "House"),
                    ("LAND", "Land"),
                    ("COMMERCIAL", "Commercial"),
                ],
                default="APARTMENT",
                max_length=20,
                help_text="Default PropertyRaw.property_type for records produced by this source.",
            ),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="scrapersource",
            name="offer_url_prefix",
            field=models.CharField(
                blank=True,
                help_text="Base URL for item links (PORTAL_LISTING sources only).",
                max_length=500,
            ),
        ),
        migrations.CreateModel(
            name="ScraperSourceStage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "stage_name",
                    models.CharField(
                        help_text="e.g. 'list_pages', 'discover' — must match shared.consts.Stage values.",
                        max_length=100,
                    ),
                ),
                (
                    "order",
                    models.PositiveIntegerField(help_text="Execution order within this source, starting at 1."),
                ),
                (
                    "code_ref",
                    models.CharField(
                        help_text="Dotted reference to the Stage class in the scraper repo's STAGE_REGISTRY, e.g. 'otodom.ListPagesStage'.",
                        max_length=255,
                    ),
                ),
                (
                    "source",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="stages",
                        to="scraper_source.scrapersource",
                    ),
                ),
            ],
            options={
                "db_table": "scraper_source_stage",
                "ordering": ["source", "order"],
            },
        ),
        migrations.AddConstraint(
            model_name="scrapersourcestage",
            constraint=models.UniqueConstraint(fields=("source", "stage_name"), name="uniq_source_stage_name"),
        ),
        migrations.AddConstraint(
            model_name="scrapersourcestage",
            constraint=models.UniqueConstraint(fields=("source", "order"), name="uniq_source_stage_order"),
        ),
    ]
