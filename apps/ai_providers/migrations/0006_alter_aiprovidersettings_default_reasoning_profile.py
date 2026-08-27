# Generated manually for tightening default reasoning profile dropdown choices.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("ai_providers", "0005_reasoningproviderprofile_show_on_dashboard"),
    ]

    operations = [
        migrations.AlterField(
            model_name="aiprovidersettings",
            name="default_reasoning_profile",
            field=models.ForeignKey(
                blank=True,
                limit_choices_to={"is_active": True, "show_on_dashboard": True},
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="default_reasoning_settings",
                to="ai_providers.reasoningproviderprofile",
            ),
        ),
    ]
