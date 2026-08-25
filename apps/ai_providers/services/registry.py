from apps.ai_providers.models import ProviderType

from .adapters import (
    GeminiProviderAdapter,
    GroqProviderAdapter,
    LocalOpenAIProviderAdapter,
    OllamaProviderAdapter,
    OpenAIProviderAdapter,
)


class ProviderRegistry:
    """Registry from provider type to adapter implementation."""

    _registry = {
        ProviderType.OPENAI: OpenAIProviderAdapter,
        ProviderType.GEMINI: GeminiProviderAdapter,
        ProviderType.GROQ: GroqProviderAdapter,
        ProviderType.OLLAMA: OllamaProviderAdapter,
        ProviderType.LOCAL_OPENAI: LocalOpenAIProviderAdapter,
    }

    @classmethod
    def get_adapter_class(cls, provider_type):
        adapter_class = cls._registry.get(provider_type)
        if adapter_class is None:
            raise ValueError(f"Unsupported provider type: {provider_type}")
        return adapter_class
