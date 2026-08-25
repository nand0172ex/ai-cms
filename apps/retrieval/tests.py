from django.test import TestCase

from apps.knowledge.models import KnowledgeBase
from apps.retrieval.models import RetrievalProfile


class RetrievalTests(TestCase):
	def test_profile_creation(self):
		kb = KnowledgeBase.objects.create(name="KB", slug="kb", collection_name="kb")
		profile = RetrievalProfile.objects.create(name="Default", knowledge_base=kb)
		self.assertEqual(profile.top_k, 5)
