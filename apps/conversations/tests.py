from django.test import TestCase

from apps.conversations.models import AIAssistant, Conversation, Message


class ConversationTests(TestCase):
	def test_create_conversation_and_message(self):
		assistant = AIAssistant.objects.create(name="Helper", slug="helper")
		conv = Conversation.objects.create(assistant=assistant, title="T1")
		message = Message.objects.create(conversation=conv, role=Message.Role.USER, content="Hello")
		self.assertEqual(message.role, Message.Role.USER)
