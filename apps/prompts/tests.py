from django.test import TestCase

from apps.prompts.models import PromptTemplate


class PromptTemplateTests(TestCase):
	def test_render_replaces_variables(self):
		template = PromptTemplate.objects.create(
			key="answer",
			name="Answer Prompt",
			version=1,
			template="Hello {{ name }}",
		)
		self.assertEqual(template.render({"name": "World"}), "Hello World")

	def test_slug_auto_generated(self):
		template = PromptTemplate.objects.create(
			key="citation",
			name="Citation Prompt",
			version=2,
			template="X",
		)
		self.assertEqual(template.slug, "citation-v2")
