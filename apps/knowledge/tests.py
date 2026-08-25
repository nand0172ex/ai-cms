from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.knowledge.models import KnowledgeBase, QdrantConnection
from apps.knowledge.services import CollectionManagementService, QdrantRepository
from apps.tenants.models import Tenant


class KnowledgeModelTests(TestCase):
	def setUp(self):
		self.tenant = Tenant.objects.create(name="Tenant A")

	def test_slug_and_collection_auto_generated(self):
		kb = KnowledgeBase.objects.create(name="Product Docs")
		self.assertEqual(kb.slug, "product-docs")
		self.assertEqual(kb.collection_name, "product_docs")

	def test_effective_collection_name_includes_tenant(self):
		kb = KnowledgeBase.objects.create(
			tenant=self.tenant,
			name="Tenant Docs",
			collection_name="tenant_docs",
			slug="tenant-docs",
		)
		self.assertEqual(kb.effective_collection_name, "tenant-a__tenant_docs")

	def test_similarity_threshold_validation(self):
		kb = KnowledgeBase(
			name="Invalid KB",
			slug="invalid-kb",
			collection_name="invalid_kb",
			similarity_threshold=1.2,
		)
		with self.assertRaises(ValidationError):
			kb.full_clean()


class QdrantRepositoryTests(TestCase):
	@patch("apps.knowledge.services.repository.QdrantClient")
	def test_create_collection_when_missing(self, qdrant_client_mock):
		connection = QdrantConnection(name="Local", slug="local", url="http://localhost:6333")
		client = qdrant_client_mock.return_value
		client.get_collections.return_value = SimpleNamespace(collections=[])

		repository = QdrantRepository(connection)
		created = repository.create_collection("sample_collection", 1536)

		self.assertTrue(created)
		client.create_collection.assert_called_once()

	@patch("apps.knowledge.services.repository.QdrantClient")
	def test_collection_exists_true(self, qdrant_client_mock):
		connection = QdrantConnection(name="Local", slug="local", url="http://localhost:6333")
		client = qdrant_client_mock.return_value
		client.get_collections.return_value = SimpleNamespace(
			collections=[SimpleNamespace(name="sample_collection")]
		)

		repository = QdrantRepository(connection)
		self.assertTrue(repository.collection_exists("sample_collection"))


class CollectionServiceTests(TestCase):
	def setUp(self):
		self.tenant = Tenant.objects.create(name="Scoped Tenant")
		self.connection = QdrantConnection.objects.create(
			tenant=self.tenant,
			name="Tenant Qdrant",
			slug="tenant-qdrant",
			url="http://localhost:6333",
			is_default=True,
		)
		self.kb = KnowledgeBase.objects.create(
			tenant=self.tenant,
			qdrant_connection=self.connection,
			name="Support KB",
			slug="support-kb",
			collection_name="support_kb",
		)

	@patch("apps.knowledge.services.collection_service.QdrantRepository")
	def test_refresh_stats_updates_document_count(self, repository_mock):
		repository_mock.return_value.get_collection_stats.return_value = {
			"collection_name": self.kb.effective_collection_name,
			"points_count": 42,
			"vectors_count": 42,
			"status": "green",
			"vector_size": 1536,
		}

		stats = CollectionManagementService(self.kb).refresh_stats()
		self.kb.refresh_from_db()

		self.assertEqual(self.kb.document_count, 42)
		self.assertEqual(stats["points_count"], 42)


class KnowledgeStatsEndpointTests(TestCase):
	def setUp(self):
		user_model = get_user_model()
		self.user = user_model.objects.create_user(
			username="kbtester",
			password="pass12345",
			is_staff=True,
		)
		self.kb = KnowledgeBase.objects.create(
			name="API KB",
			slug="api-kb",
			collection_name="api_kb",
		)

	@patch("apps.knowledge.views.CollectionManagementService")
	def test_stats_endpoint_returns_json(self, service_mock):
		self.client.force_login(self.user)
		service_instance = Mock()
		service_instance.refresh_stats.return_value = {
			"collection_name": "api_kb",
			"points_count": 3,
		}
		service_mock.return_value = service_instance

		response = self.client.get("/api/v1/knowledge-bases/api-kb/stats/")

		self.assertEqual(response.status_code, 200)
		body = response.json()
		self.assertEqual(body["knowledge_base"], "api-kb")
		self.assertEqual(body["stats"]["points_count"], 3)
