# Generated manually for reasoning provider profile dashboard visibility toggle.

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("ai_providers", "0004_aiprovidersettings_visibility_toggles"),
    ]

    operations = [
        migrations.AddField(
            model_name="reasoningproviderprofile",
            name="show_on_dashboard",
            field=models.BooleanField(
                default=True,
                help_text="If disabled, this profile is hidden from Qdrant dashboard reasoning provider list.",
                verbose_name="Visible in dashboard",
            ),
        ),
        migrations.AlterField(
            model_name="reasoningproviderprofile",
            name="is_active",
            field=models.BooleanField(
                default=True,
                help_text="Turn off to fully disable this reasoning profile.",
                verbose_name="Active (runtime enabled)",
            ),
        ),
    ]
