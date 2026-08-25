from django.db import migrations


DEFAULTS = {
    "ollama": {"base_url": "http://127.0.0.1:11434/v1/models", "connection_timeout_seconds": 5},
    "local-models": {"base_url": "", "connection_timeout_seconds": 10},
}


def apply_defaults(apps, schema_editor):
    EmbeddingProfile = apps.get_model("knowledge", "EmbeddingProfile")
    for slug, fields in DEFAULTS.items():
        EmbeddingProfile.objects.filter(slug=slug, base_url="").update(**fields)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("knowledge", "0006_embeddingprofile_api_key_and_more"),
    ]

    operations = [
        migrations.RunPython(apply_defaults, noop),
    ]
