from django.test import TestCase

from apps.tenants.models import Tenant


class TenantModelTests(TestCase):
	def test_slug_auto_generated_from_name(self):
		tenant = Tenant.objects.create(name="Acme Corporation")
		self.assertEqual(tenant.slug, "acme-corporation")

	def test_string_representation(self):
		tenant = Tenant.objects.create(name="Northwind")
		self.assertEqual(str(tenant), "Northwind")
