from urllib.parse import urlparse

import httpx
from django.core.exceptions import ValidationError

from langchain_google_genai import (
    ChatGoogleGenerativeAI,
    GoogleGenerativeAIEmbeddings,
)
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from apps.ai_providers.models import ProviderType
from .interfaces import BaseProviderAdapter


class OpenAIProviderAdapter(BaseProviderAdapter):
    def validate_config(self):
        if not self.provider_config.get_api_key():
            raise ValidationError("Missing OpenAI API key environment variable value.")

    def build_chat_model(self, llm_config):
        self.validate_config()
        return ChatOpenAI(
            model=llm_config.model_name,
            api_key=self.provider_config.get_api_key(),
            base_url=self.provider_config.base_url or None,
            temperature=llm_config.temperature,
            max_tokens=llm_config.max_tokens,
            timeout=self.provider_config.timeout_seconds,
            model_kwargs=llm_config.model_kwargs,
        )

    def build_embeddings_model(self, embedding_config):
        self.validate_config()
        return OpenAIEmbeddings(
            model=embedding_config.model_name,
            api_key=self.provider_config.get_api_key(),
            base_url=self.provider_config.base_url or None,
            model_kwargs=embedding_config.model_kwargs,
        )


class GeminiProviderAdapter(BaseProviderAdapter):
    def validate_config(self):
        if not self.provider_config.get_api_key():
            raise ValidationError("Missing Gemini API key environment variable value.")

    def build_chat_model(self, llm_config):
        self.validate_config()
        return ChatGoogleGenerativeAI(
            model=llm_config.model_name,
            google_api_key=self.provider_config.get_api_key(),
            temperature=llm_config.temperature,
            max_output_tokens=llm_config.max_tokens,
            **llm_config.model_kwargs,
        )

    def build_embeddings_model(self, embedding_config):
        self.validate_config()
        return GoogleGenerativeAIEmbeddings(
            model=embedding_config.model_name,
            google_api_key=self.provider_config.get_api_key(),
            **embedding_config.model_kwargs,
        )


class OpenAICompatibleProviderAdapter(BaseProviderAdapter):
    """Shared adapter for OpenAI-compatible providers (Groq/Ollama/local)."""

    def __init__(self, provider_config, fallback_base_url="", fallback_api_key=""):
        super().__init__(provider_config)
        self.fallback_base_url = fallback_base_url
        self.fallback_api_key = fallback_api_key

    def _resolve_api_key(self):
        api_key = self.provider_config.get_api_key()
        return api_key or self.fallback_api_key

    def _resolve_base_url(self):
        base_url = self.provider_config.base_url or self.fallback_base_url
        if self.provider_config.provider_type in {ProviderType.OLLAMA, ProviderType.LOCAL_OPENAI}:
            base_url = base_url.replace("http://localhost", "http://127.0.0.1")
            base_url = base_url.replace("https://localhost", "https://127.0.0.1")
        return base_url

    def _should_bypass_env_proxy(self):
        base_url = self._resolve_base_url() or ""
        hostname = (urlparse(base_url).hostname or "").lower()
        if self.provider_config.provider_type in {ProviderType.OLLAMA, ProviderType.LOCAL_OPENAI}:
            return True
        return hostname in {"localhost", "127.0.0.1", "0.0.0.0"}

    def _build_http_client(self):
        if self._should_bypass_env_proxy():
            return httpx.Client(trust_env=False, timeout=self.provider_config.timeout_seconds)
        return None

    def validate_config(self):
        if self.provider_config.provider_type in {ProviderType.GROQ, ProviderType.LOCAL_OPENAI}:
            if not self._resolve_api_key():
                raise ValidationError("Missing API key for OpenAI-compatible provider.")
        if not self._resolve_base_url() and self.provider_config.provider_type != ProviderType.GROQ:
            raise ValidationError("Base URL is required for this provider.")

    def build_chat_model(self, llm_config):
        self.validate_config()
        http_client = self._build_http_client()
        return ChatOpenAI(
            model=llm_config.model_name,
            api_key=self._resolve_api_key(),
            base_url=self._resolve_base_url() or None,
            temperature=llm_config.temperature,
            max_tokens=llm_config.max_tokens,
            timeout=self.provider_config.timeout_seconds,
            model_kwargs=llm_config.model_kwargs,
            http_client=http_client,
        )

    def build_embeddings_model(self, embedding_config):
        self.validate_config()
        return OpenAIEmbeddings(
            model=embedding_config.model_name,
            api_key=self._resolve_api_key(),
            base_url=self._resolve_base_url() or None,
            model_kwargs=embedding_config.model_kwargs,
        )


class GroqProviderAdapter(OpenAICompatibleProviderAdapter):
    def __init__(self, provider_config):
        super().__init__(
            provider_config,
            fallback_base_url="https://api.groq.com/openai/v1",
            fallback_api_key="",
        )


class OllamaProviderAdapter(OpenAICompatibleProviderAdapter):
    def __init__(self, provider_config):
        super().__init__(
            provider_config,
            fallback_base_url="http://127.0.0.1:11434/v1",
            fallback_api_key="ollama",
        )


class LocalOpenAIProviderAdapter(OpenAICompatibleProviderAdapter):
    def __init__(self, provider_config):
        super().__init__(
            provider_config,
            fallback_base_url="http://127.0.0.1:8001/v1",
            fallback_api_key="local-dev-key",
        )
