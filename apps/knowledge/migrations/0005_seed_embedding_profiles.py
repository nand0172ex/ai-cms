from django.db import migrations


PROFILES = [
    dict(
        name="Default",
        slug="default",
        provider_type="default",
        model_name="Deterministic Hash Embedding",
        embedding_dimensions=1536,
        best_use_case="Zero-setup embedding used automatically when no profile is selected.",
        performance_rating=3,
        cost_indicator="free",
        capability="offline",
        highlights=[
            "No external dependency",
            "Works out of the box",
            "Backward compatible with existing uploads",
        ],
        why_choose="Keep using this if you don't need to change anything - it's what every upload uses today.",
        badge_recommended=True,
        badge_cost_effective=True,
        badge_fully_offline=True,
        badge_fastest=False,
        badge_highest_accuracy=False,
        is_default=True,
        sort_order=0,
    ),
    dict(
        name="HuggingFace",
        slug="huggingface",
        provider_type="huggingface",
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        embedding_dimensions=384,
        best_use_case="Good general purpose embeddings with a large model selection.",
        performance_rating=4,
        cost_indicator="low",
        capability="online",
        highlights=[
            "Good general purpose embeddings",
            "Large model selection",
            "Cloud based",
        ],
        why_choose="Choose HuggingFace when you want flexibility across many open embedding models without managing local infrastructure.",
        badge_recommended=False,
        badge_cost_effective=True,
        badge_fully_offline=False,
        badge_fastest=False,
        badge_highest_accuracy=False,
        is_default=False,
        sort_order=1,
    ),
    dict(
        name="OpenAI",
        slug="openai",
        provider_type="openai",
        model_name="text-embedding-3-small",
        embedding_dimensions=1536,
        best_use_case="High quality semantic search with the best retrieval accuracy.",
        performance_rating=5,
        cost_indicator="medium",
        capability="online",
        highlights=[
            "High quality semantic search",
            "Best retrieval accuracy",
            "API cost applicable",
        ],
        why_choose="Choose OpenAI when retrieval accuracy matters more than cost and you're comfortable with an external API dependency.",
        badge_recommended=False,
        badge_cost_effective=False,
        badge_fully_offline=False,
        badge_fastest=False,
        badge_highest_accuracy=True,
        is_default=False,
        sort_order=2,
    ),
    dict(
        name="Azure OpenAI",
        slug="azure-openai",
        provider_type="azure_openai",
        model_name="text-embedding-3-small (Azure deployment)",
        embedding_dimensions=1536,
        best_use_case="Enterprise-grade OpenAI models with Azure compliance and networking controls.",
        performance_rating=5,
        cost_indicator="medium",
        capability="online",
        highlights=[
            "Enterprise compliance and SLAs",
            "Same quality as OpenAI models",
            "Runs inside your Azure tenant",
        ],
        why_choose="Choose Azure OpenAI when you need OpenAI-grade quality but must keep traffic inside an approved Azure environment.",
        badge_recommended=False,
        badge_cost_effective=False,
        badge_fully_offline=False,
        badge_fastest=False,
        badge_highest_accuracy=True,
        is_default=False,
        sort_order=3,
    ),
    dict(
        name="Ollama Local",
        slug="ollama",
        provider_type="ollama",
        model_name="nomic-embed-text",
        embedding_dimensions=768,
        best_use_case="Completely local embeddings with no external dependency.",
        performance_rating=3,
        cost_indicator="free",
        capability="offline",
        highlights=[
            "Completely local",
            "No external dependency",
            "Better for restricted environments",
        ],
        why_choose="Choose Ollama when you need local inference for privacy or restricted-network environments without any cloud calls.",
        badge_recommended=False,
        badge_cost_effective=True,
        badge_fully_offline=True,
        badge_fastest=True,
        badge_highest_accuracy=False,
        is_default=False,
        sort_order=4,
    ),
    dict(
        name="Local Models",
        slug="local-models",
        provider_type="local",
        model_name="Self-hosted embedding model",
        embedding_dimensions=1024,
        best_use_case="Fully offline, enterprise friendly embedding for locked-down infrastructure.",
        performance_rating=3,
        cost_indicator="free",
        capability="offline",
        highlights=[
            "Fully offline",
            "Enterprise friendly",
            "Requires local compute resources",
        ],
        why_choose="Choose Local Models when compliance requires all data and computation to remain on your own infrastructure.",
        badge_recommended=False,
        badge_cost_effective=True,
        badge_fully_offline=True,
        badge_fastest=False,
        badge_highest_accuracy=False,
        is_default=False,
        sort_order=5,
    ),
    dict(
        name="Custom API",
        slug="custom-api",
        provider_type="custom",
        model_name="Bring your own embedding endpoint",
        embedding_dimensions=1536,
        best_use_case="Connect any OpenAI-compatible or proprietary embedding API you already operate.",
        performance_rating=3,
        cost_indicator="medium",
        capability="hybrid",
        highlights=[
            "Bring your own provider",
            "Works with OpenAI-compatible APIs",
            "Flexible for future providers",
        ],
        why_choose="Choose Custom API when you already run or plan to run your own embedding service and want it available as a selectable option.",
        badge_recommended=False,
        badge_cost_effective=False,
        badge_fully_offline=False,
        badge_fastest=False,
        badge_highest_accuracy=False,
        is_default=False,
        sort_order=6,
    ),
]


def seed_profiles(apps, schema_editor):
    EmbeddingProfile = apps.get_model("knowledge", "EmbeddingProfile")
    for data in PROFILES:
        EmbeddingProfile.objects.update_or_create(slug=data["slug"], defaults=data)


def remove_profiles(apps, schema_editor):
    EmbeddingProfile = apps.get_model("knowledge", "EmbeddingProfile")
    EmbeddingProfile.objects.filter(slug__in=[p["slug"] for p in PROFILES]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("knowledge", "0004_embeddingprofile_alter_vectordbsettings_options"),
    ]

    operations = [
        migrations.RunPython(seed_profiles, remove_profiles),
    ]
