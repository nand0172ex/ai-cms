from django.shortcuts import get_object_or_404, render

from apps.conversations.models import AIAssistant


def assistant_chat_page(request, slug):
	assistant = get_object_or_404(AIAssistant, slug=slug, is_active=True)
	return render(request, "conversations/chat_page.html", {"assistant": assistant})


def ai_assistant_home(request):
	return render(request, "ai_assistant_home.html")
