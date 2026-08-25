from django.test import TestCase

from apps.audit.models import AuditEvent


class AuditTests(TestCase):
	def test_create_audit_event(self):
		event = AuditEvent.objects.create(action="chat.request", resource_type="conversation", resource_id="1")
		self.assertEqual(event.action, "chat.request")
