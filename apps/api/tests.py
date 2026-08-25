from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from apps.conversations.models import AIAssistant
from apps.ingestion.models import UploadedDocument
from apps.knowledge.models import KnowledgeBase


class APITests(TestCase):
	def setUp(self):
		self.assistant = AIAssistant.objects.create(name="Public Bot", slug="public-bot", is_active=True)
		self.kb = KnowledgeBase.objects.create(name="KB", slug="kb", collection_name="kb")

	def test_assistants_endpoint(self):
		response = self.client.get("/api/v1/assistants/")
		self.assertEqual(response.status_code, 200)

	def test_knowledge_bases_endpoint(self):
		response = self.client.get("/api/v1/knowledge-bases/")
		self.assertEqual(response.status_code, 200)

	def test_chat_endpoint(self):
		response = self.client.post(
			"/api/v1/chat/",
			data={"assistant_slug": self.assistant.slug, "prompt": "hello"},
			content_type="application/json",
		)
		self.assertEqual(response.status_code, 200)

	def test_chat_stream_endpoint(self):
		response = self.client.post(
			"/api/v1/chat/stream/",
			data={"assistant_slug": self.assistant.slug, "prompt": "hello"},
			content_type="application/json",
		)
		self.assertEqual(response.status_code, 200)

	def test_job_status_endpoint(self):
		response = self.client.get("/api/v1/jobs/status/")
		self.assertEqual(response.status_code, 200)

	@patch("apps.knowledge.services.repository.QdrantRepository.upsert_points", return_value=1)
	@patch("apps.knowledge.services.repository.QdrantRepository.create_collection", return_value=True)
	def test_upload_file_endpoint(self, _mock_create_collection, _mock_upsert_points):
		upload = SimpleUploadedFile("notes.txt", b"This is a sample upload for qdrant indexing.")
		response = self.client.post(
			"/api/v1/upload-file/",
			data={"file": upload, "knowledge_base_slug": self.kb.slug},
		)
		self.assertEqual(response.status_code, 200)
		payload = response.json()
		self.assertEqual(payload["status"], "success")
		self.assertGreaterEqual(payload["chunk_count"], 1)
		self.assertTrue(
			UploadedDocument.objects.filter(
				id=payload["document_id"],
				is_processed=True,
			).exists()
		)

	def test_error_summary_endpoint(self):
		response = self.client.get("/api/v1/errors/summary/")
		self.assertEqual(response.status_code, 200)
