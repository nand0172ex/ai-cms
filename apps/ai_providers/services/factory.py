from apps.ai_providers.services.registry import ProviderRegistry


class ProviderFactory:
    """Factory for provider adapters and LangChain model instances."""

    @staticmethod
    def get_adapter(provider_config):
        adapter_class = ProviderRegistry.get_adapter_class(provider_config.provider_type)
        return adapter_class(provider_config)

    @classmethod
    def validate_provider(cls, provider_config):
        adapter = cls.get_adapter(provider_config)
        adapter.validate_config()
        return True

    @classmethod
    def build_chat_model(cls, llm_model_config):
        adapter = cls.get_adapter(llm_model_config.provider)
        return adapter.build_chat_model(llm_model_config)

    @classmethod
    def build_embeddings_model(cls, embedding_model_config):
        adapter = cls.get_adapter(embedding_model_config.provider)
        return adapter.build_embeddings_model(embedding_model_config)
