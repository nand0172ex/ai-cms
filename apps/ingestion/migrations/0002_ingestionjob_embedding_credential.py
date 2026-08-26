import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_userembeddingcredential"),
        ("ingestion", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="ingestionjob",
            name="embedding_credential",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="ingestion_jobs",
                to="accounts.userembeddingcredential",
            ),
        ),
    ]
