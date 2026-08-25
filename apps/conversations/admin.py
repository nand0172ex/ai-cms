from django.contrib import admin

from apps.conversations.models import AIAssistant, Conversation, Message


@admin.register(AIAssistant)
class AIAssistantAdmin(admin.ModelAdmin):
	list_display = ("name", "tenant", "agent_mode", "llm_model", "is_public", "is_active")
	list_filter = ("tenant", "agent_mode", "is_public", "is_active")


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
	list_display = ("id", "assistant", "user", "session_key", "is_active", "updated_at")
	list_filter = ("assistant", "is_active")


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
	list_display = ("conversation", "role", "created_at")
	list_filter = ("role",)
