import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("domain", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ScraperSource",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(
                    help_text="Unique identifier used in Job.source, e.g. 'otodom/sell/apartment/owner'",
                    max_length=255,
                    unique=True,
                )),
                ("offer_url_prefix", models.CharField(
                    blank=True,
                    help_text="Base URL for item links, available as OFFER_URL_PREFIX in snippets",
                    max_length=500,
                )),
                ("is_active", models.BooleanField(default=True)),
                ("notes", models.TextField(blank=True)),
                ("preamble_code", models.TextField(blank=True)),
                ("list_pages_code", models.TextField()),
                ("list_items_code", models.TextField()),
                ("get_item_code", models.TextField()),
                ("domain", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="scraper_sources",
                    to="domain.domain",
                )),
            ],
            options={
                "db_table": "scraper_source",
                "ordering": ["name"],
            },
        ),
    ]
