# Generated manually for AI provider visibility toggles and dropdown constraints.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("ai_providers", "0003_reasoningproviderprofile_aiprovidersettings_default_reasoning_profile"),
    ]

    operations = [
        migrations.AddField(
            model_name="aiprovidersettings",
            name="enable_embedding_profiles",
            field=models.BooleanField(
                default=True,
                help_text="If disabled, embedding profile selection/configuration is hidden from upload/dashboard UI.",
            ),
        ),
        migrations.AddField(
            model_name="aiprovidersettings",
            name="enable_reasoning_profiles",
            field=models.BooleanField(
                default=True,
                help_text="If disabled, reasoning profile selection is hidden and runtime falls back to legacy LLM model settings.",
            ),
        ),
        migrations.AlterField(
            model_name="aiprovidersettings",
            name="active_provider_type",
            field=models.CharField(
                choices=[
                    ("openai", "OpenAI"),
                    ("gemini", "Google Gemini"),
                    ("ollama", "Ollama Local"),
                    ("local_openai", "OpenAI Compatible"),
                ],
                default="openai",
                max_length=32,
            ),
        ),
        migrations.AlterField(
            model_name="aiprovidersettings",
            name="default_provider",
            field=models.ForeignKey(
                blank=True,
                limit_choices_to={"is_active": True},
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="default_provider_settings",
                to="ai_providers.aiproviderconfig",
            ),
        ),
        migrations.AlterField(
            model_name="aiprovidersettings",
            name="default_llm_model",
            field=models.ForeignKey(
                blank=True,
                limit_choices_to={"is_active": True},
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="default_llm_settings",
                to="ai_providers.llmmodelconfig",
            ),
        ),
        migrations.AlterField(
            model_name="aiprovidersettings",
            name="default_embedding_model",
            field=models.ForeignKey(
                blank=True,
                limit_choices_to={"is_active": True},
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="default_embedding_settings",
                to="ai_providers.embeddingmodelconfig",
            ),
        ),
        migrations.AlterField(
            model_name="aiprovidersettings",
            name="default_reasoning_profile",
            field=models.ForeignKey(
                blank=True,
                limit_choices_to={"is_active": True},
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="default_reasoning_settings",
                to="ai_providers.reasoningproviderprofile",
            ),
        ),
    ]
