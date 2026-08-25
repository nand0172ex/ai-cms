from abc import ABC, abstractmethod


class BaseProviderAdapter(ABC):
    """Contract for provider-specific adapter implementations."""

    def __init__(self, provider_config):
        self.provider_config = provider_config

    @abstractmethod
    def validate_config(self):
        """Validate provider configuration and secret availability."""

    @abstractmethod
    def build_chat_model(self, llm_config):
        """Return a configured LangChain chat model."""

    @abstractmethod
    def build_embeddings_model(self, embedding_config):
        """Return a configured LangChain embeddings model."""
