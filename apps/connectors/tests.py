from django.test import TestCase

from apps.connectors.models import ConnectorConfig
from apps.knowledge.models import KnowledgeBase


class ConnectorModelTests(TestCase):
	def test_connector_creation(self):
		kb = KnowledgeBase.objects.create(name="KB", slug="kb", collection_name="kb")
		config = ConnectorConfig.objects.create(
			knowledge_base=kb,
			name="Jira Connector",
			connector_type=ConnectorConfig.ConnectorType.JIRA,
			base_url="https://example.atlassian.net",
			token_env_var="JIRA_TOKEN",
		)
		self.assertEqual(config.connector_type, ConnectorConfig.ConnectorType.JIRA)
