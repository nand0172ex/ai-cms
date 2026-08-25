from django.conf import settings
from django.db import models
from django.utils.text import slugify
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.contrib.settings.models import BaseSiteSetting, register_setting

from apps.core.models import AbstractBaseModel


class AIAssistant(AbstractBaseModel):
    class AgentMode(models.TextChoices):
        RAG = "rag", "RAG Agent"
        LLM_ONLY = "llm_only", "LLM Only"
        HYBRID = "hybrid", "Hybrid"

    tenant = models.ForeignKey("tenants.Tenant", null=True, blank=True, on_delete=models.CASCADE)
    name = models.CharField(max_length=140)
    slug = models.SlugField(max_length=170)
    description = models.TextField(blank=True)
    system_prompt = models.ForeignKey("prompts.PromptTemplate", null=True, blank=True, on_delete=models.SET_NULL)
    retrieval_profile = models.ForeignKey("retrieval.RetrievalProfile", null=True, blank=True, on_delete=models.SET_NULL)
    llm_model = models.ForeignKey("ai_providers.LLMModelConfig", null=True, blank=True, on_delete=models.SET_NULL)
    agent_mode = models.CharField(max_length=20, choices=AgentMode.choices, default=AgentMode.RAG)
    is_public = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = [("tenant", "slug")]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Conversation(AbstractBaseModel):
    assistant = models.ForeignKey(AIAssistant, on_delete=models.CASCADE, related_name="conversations")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    session_key = models.CharField(max_length=80, blank=True)
    title = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)


class Message(AbstractBaseModel):
    class Role(models.TextChoices):
        USER = "user", "User"
        ASSISTANT = "assistant", "Assistant"
        SYSTEM = "system", "System"

    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=20, choices=Role.choices)
    content = models.TextField()
    citations = models.JSONField(default=list, blank=True)
    token_usage = models.JSONField(default=dict, blank=True)


@register_setting
class AssistantRuntimeSettings(BaseSiteSetting):
    """Global assistant routing settings in Wagtail Settings sidebar."""

    default_assistant = models.ForeignKey(
        AIAssistant,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="default_assistant_settings",
    )
    preferred_agent_mode = models.CharField(
        max_length=20,
        choices=AIAssistant.AgentMode.choices,
        default=AIAssistant.AgentMode.RAG,
    )
    allow_anonymous_chat = models.BooleanField(default=True)
    max_requests_per_minute = models.PositiveIntegerField(default=60)

    panels = [
        MultiFieldPanel(
            [
                FieldPanel("default_assistant"),
                FieldPanel("preferred_agent_mode"),
            ],
            heading="Agent Router",
        ),
        MultiFieldPanel(
            [
                FieldPanel("allow_anonymous_chat"),
                FieldPanel("max_requests_per_minute"),
            ],
            heading="Public Chat Guardrails",
        ),
    ]

    class Meta:
        verbose_name = "Assistant Runtime Settings"
