from abc import ABC, abstractmethod

from apps.ai_providers.services import ProviderFactory


class BaseEmbeddingService(ABC):
    @abstractmethod
    def embed_texts(self, embedding_model_config, texts):
        pass


class LangChainEmbeddingService(BaseEmbeddingService):
    def embed_texts(self, embedding_model_config, texts):
        model = ProviderFactory.build_embeddings_model(embedding_model_config)
        return model.embed_documents(texts)
