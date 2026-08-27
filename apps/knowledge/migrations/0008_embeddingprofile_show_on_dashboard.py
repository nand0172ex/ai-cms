# Generated manually for embedding profile dashboard visibility toggle.

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("knowledge", "0007_embedding_profile_connection_defaults"),
    ]

    operations = [
        migrations.AddField(
            model_name="embeddingprofile",
            name="show_on_dashboard",
            field=models.BooleanField(
                default=True,
                help_text="If disabled, this profile is hidden from Qdrant dashboard provider lists.",
                verbose_name="Visible in dashboard",
            ),
        ),
        migrations.AlterField(
            model_name="embeddingprofile",
            name="is_active",
            field=models.BooleanField(
                default=True,
                help_text="Turn off to fully disable this provider profile.",
                verbose_name="Active (runtime enabled)",
            ),
        ),
    ]
