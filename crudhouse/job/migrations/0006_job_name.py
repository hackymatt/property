from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("job", "0005_alter_jobrunlog_source"),
    ]

    operations = [
        migrations.AddField(
            model_name="job",
            name="name",
            field=models.CharField(max_length=255, unique=True),
        ),
    ]
