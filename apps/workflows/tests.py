from django.test import TestCase

from apps.workflows.models import WorkflowRun


class WorkflowRunTests(TestCase):
	def test_default_status_started(self):
		run = WorkflowRun.objects.create(query="hello")
		self.assertEqual(run.status, WorkflowRun.Status.STARTED)
