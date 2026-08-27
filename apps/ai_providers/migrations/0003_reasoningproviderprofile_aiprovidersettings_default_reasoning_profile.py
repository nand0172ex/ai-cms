# Generated manually for snippet-based reasoning provider profiles.

import django.db.models.deletion
from django.db import migrations, models


def seed_reasoning_profiles(apps, schema_editor):
    ReasoningProviderProfile = apps.get_model("ai_providers", "ReasoningProviderProfile")

    defaults = [
        {
            "name": "OpenAI GPT-4o Mini",
            "slug": "openai-gpt-4o-mini",
            "provider_type": "openai",
            "model_name": "gpt-4o-mini",
            "endpoint_url": "https://api.openai.com/v1",
            "api_key_env_var": "OPENAI_API_KEY",
            "timeout_seconds": 60,
            "temperature": 0.2,
            "max_tokens": 1024,
            "top_p": 1.0,
            "is_default": False,
            "is_active": True,
            "sort_order": 10,
        },
        {
            "name": "Gemini 1.5 Flash",
            "slug": "gemini-1-5-flash",
            "provider_type": "gemini",
            "model_name": "gemini-1.5-flash",
            "endpoint_url": "https://generativelanguage.googleapis.com/v1beta",
            "api_key_env_var": "GEMINI_API_KEY",
            "timeout_seconds": 60,
            "temperature": 0.2,
            "max_tokens": 1024,
            "top_p": 1.0,
            "is_default": False,
            "is_active": True,
            "sort_order": 20,
        },
        {
            "name": "Ollama Local",
            "slug": "ollama-local",
            "provider_type": "ollama",
            "model_name": "llama3:8b",
            "endpoint_url": "http://127.0.0.1:11434/v1",
            "timeout_seconds": 60,
            "temperature": 0.2,
            "max_tokens": 1024,
            "top_p": 1.0,
            "is_default": True,
            "is_active": True,
            "sort_order": 30,
        },
        {
            "name": "OpenAI-Compatible Local",
            "slug": "openai-compatible-local",
            "provider_type": "openai_compatible",
            "model_name": "local-model",
            "endpoint_url": "http://127.0.0.1:8001/v1",
            "api_key_env_var": "LOCAL_OPENAI_API_KEY",
            "timeout_seconds": 60,
            "temperature": 0.2,
            "max_tokens": 1024,
            "top_p": 1.0,
            "is_default": False,
            "is_active": True,
            "sort_order": 40,
        },
    ]

    for item in defaults:
        ReasoningProviderProfile.objects.update_or_create(
            slug=item["slug"],
            defaults=item,
        )


def set_default_reasoning_profile(apps, schema_editor):
    AIProviderSettings = apps.get_model("ai_providers", "AIProviderSettings")
    ReasoningProviderProfile = apps.get_model("ai_providers", "ReasoningProviderProfile")

    default_profile = ReasoningProviderProfile.objects.filter(is_default=True, is_active=True).first()
    if not default_profile:
        return

    for setting in AIProviderSettings.objects.all():
        if not setting.default_reasoning_profile_id:
            setting.default_reasoning_profile_id = default_profile.id
            setting.save(update_fields=["default_reasoning_profile"])


class Migration(migrations.Migration):
    dependencies = [
        ("ai_providers", "0002_aiproviderconfig_api_key_aiprovidersettings"),
    ]

    operations = [
        migrations.CreateModel(
            name="ReasoningProviderProfile",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=120)),
                ("slug", models.SlugField(blank=True, max_length=140, unique=True)),
                (
                    "provider_type",
                    models.CharField(
                        choices=[
                            ("openai", "OpenAI"),
                            ("gemini", "Google Gemini"),
                            ("ollama", "Ollama Local"),
                            ("openai_compatible", "OpenAI Compatible"),
                        ],
                        max_length=32,
                    ),
                ),
                ("model_name", models.CharField(max_length=160)),
                ("endpoint_url", models.URLField(blank=True)),
                ("api_key", models.CharField(blank=True, max_length=255)),
                (
                    "api_key_env_var",
                    models.CharField(
                        blank=True,
                        help_text="Optional environment variable containing API key.",
                        max_length=120,
                    ),
                ),
                ("headers", models.JSONField(blank=True, default=dict)),
                ("timeout_seconds", models.PositiveIntegerField(default=60)),
                ("temperature", models.FloatField(default=0.2)),
                ("max_tokens", models.PositiveIntegerField(default=1024)),
                ("top_p", models.FloatField(default=1.0)),
                ("is_default", models.BooleanField(default=False)),
                ("is_active", models.BooleanField(default=True)),
                ("sort_order", models.PositiveIntegerField(default=0)),
            ],
            options={
                "verbose_name": "Reasoning Provider Profile",
                "verbose_name_plural": "Reasoning Provider Profiles",
                "ordering": ["sort_order", "name"],
            },
        ),
        migrations.AddField(
            model_name="aiprovidersettings",
            name="default_reasoning_profile",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="default_reasoning_settings",
                to="ai_providers.reasoningproviderprofile",
            ),
        ),
        migrations.RunPython(seed_reasoning_profiles, migrations.RunPython.noop),
        migrations.RunPython(set_default_reasoning_profile, migrations.RunPython.noop),
    ]
