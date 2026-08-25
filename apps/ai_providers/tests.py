import os

from django.core.exceptions import ValidationError
from django.test import TestCase
from unittest.mock import patch

from apps.ai_providers.models import (
	AIProviderConfig,
	EmbeddingModelConfig,
	LLMModelConfig,
	ProviderType,
)
from apps.ai_providers.services import ProviderFactory
from apps.tenants.models import Tenant


class AIProviderConfigTests(TestCase):
	def setUp(self):
		self.tenant = Tenant.objects.create(name="Demo Tenant")

	def test_slug_auto_generated(self):
		provider = AIProviderConfig.objects.create(
			tenant=self.tenant,
			name="OpenAI Primary",
			provider_type=ProviderType.OPENAI,
			api_key_env_var="OPENAI_API_KEY",
		)
		self.assertEqual(provider.slug, "openai-primary")

	def test_api_key_masking_when_missing(self):
		provider = AIProviderConfig.objects.create(
			name="Ollama Local",
			provider_type=ProviderType.OLLAMA,
			base_url="http://localhost:11434/v1",
		)
		self.assertEqual(provider.masked_api_key, "(missing)")

	@patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-123456"}, clear=False)
	def test_api_key_masking_from_env_var(self):
		provider = AIProviderConfig.objects.create(
			name="OpenAI",
			provider_type=ProviderType.OPENAI,
			api_key_env_var="OPENAI_API_KEY",
		)
		self.assertTrue(provider.masked_api_key.endswith("3456"))

	def test_required_api_key_env_var_for_openai(self):
		provider = AIProviderConfig(
			name="Bad OpenAI",
			provider_type=ProviderType.OPENAI,
		)
		with self.assertRaises(ValidationError):
			provider.full_clean()

	def test_default_uniqueness_per_scope(self):
		AIProviderConfig.objects.create(
			tenant=self.tenant,
			name="Primary",
			provider_type=ProviderType.OLLAMA,
			base_url="http://localhost:11434/v1",
			is_default=True,
		)
		second = AIProviderConfig(
			tenant=self.tenant,
			name="Secondary",
			provider_type=ProviderType.OLLAMA,
			base_url="http://localhost:11434/v1",
			is_default=True,
		)
		with self.assertRaises(ValidationError):
			second.full_clean()


class ProviderFactoryTests(TestCase):
	def setUp(self):
		self.tenant = Tenant.objects.create(name="Factory Tenant")
		self.provider = AIProviderConfig.objects.create(
			tenant=self.tenant,
			name="Ollama",
			provider_type=ProviderType.OLLAMA,
			base_url="http://localhost:11434/v1",
		)
		self.llm_config = LLMModelConfig.objects.create(
			tenant=self.tenant,
			provider=self.provider,
			name="Llama Chat",
			model_name="llama3.1:8b",
			temperature=0.1,
			max_tokens=512,
		)
		self.embedding_config = EmbeddingModelConfig.objects.create(
			tenant=self.tenant,
			provider=self.provider,
			name="Nomic Embed",
			model_name="nomic-embed-text",
			vector_size=768,
		)

	def test_validate_provider_for_ollama(self):
		self.assertTrue(ProviderFactory.validate_provider(self.provider))

	@patch("apps.ai_providers.services.adapters.ChatOpenAI")
	def test_build_chat_model_uses_factory(self, chat_openai_mock):
		ProviderFactory.build_chat_model(self.llm_config)
		chat_openai_mock.assert_called_once()

	@patch("apps.ai_providers.services.adapters.OpenAIEmbeddings")
	def test_build_embeddings_model_uses_factory(self, embeddings_mock):
		ProviderFactory.build_embeddings_model(self.embedding_config)
		embeddings_mock.assert_called_once()
