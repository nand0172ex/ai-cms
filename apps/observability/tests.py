from django.test import TestCase


class ObservabilityTests(TestCase):
	def test_health_endpoint(self):
		response = self.client.get("/health/")
		self.assertEqual(response.status_code, 200)

	def test_ready_endpoint(self):
		response = self.client.get("/ready/")
		self.assertIn(response.status_code, [200, 503])
