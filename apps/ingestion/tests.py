from django.test import TestCase

from apps.ingestion.models import DataSource
from apps.knowledge.models import KnowledgeBase


class IngestionModelTests(TestCase):
	def test_create_data_source(self):
		kb = KnowledgeBase.objects.create(
			name="KB",
			slug="kb",
			collection_name="kb",
		)
		source = DataSource.objects.create(name="Uploads", knowledge_base=kb)
		self.assertEqual(source.source_type, DataSource.SourceType.UPLOAD)
