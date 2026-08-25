from django.contrib import admin
from django.contrib import messages
from django.core.exceptions import ValidationError

from apps.ai_providers.models import (
	AIProviderConfig,
	EmbeddingModelConfig,
	LLMModelConfig,
)
from apps.ai_providers.services import ProviderFactory

@admin.action(description="Validate selected provider configurations")
def validate_provider_configs(modeladmin, request, queryset):
	success_count = 0
	for provider in queryset:
		try:
			ProviderFactory.validate_provider(provider)
			success_count += 1
		except (ValidationError, ValueError) as exc:
			modeladmin.message_user(
				request,
				f"{provider.name}: {exc}",
				level=messages.ERROR,
			)

	if success_count:
		modeladmin.message_user(
			request,
			f"{success_count} provider configuration(s) validated successfully.",
			level=messages.SUCCESS,
		)


@admin.register(AIProviderConfig)
class AIProviderConfigAdmin(admin.ModelAdmin):
	list_display = (
		"name",
		"provider_type",
		"tenant",
		"is_active",
		"is_default",
		"masked_api_key_display",
		"updated_at",
	)
	list_filter = ("provider_type", "is_active", "is_default", "tenant")
	search_fields = ("name", "slug", "api_key_env_var")
	readonly_fields = ("masked_api_key_display", "created_at", "updated_at")
	actions = (validate_provider_configs,)

	fieldsets = (
		(
			"Scope",
			{
				"fields": ("tenant", "name", "slug", "provider_type"),
			},
		),
		(
			"Connection",
			{
				"fields": (
					"base_url",
					"api_key_env_var",
					"api_key",
					"masked_api_key_display",
					"headers",
					"timeout_seconds",
				),
			},
		),
		(
			"State",
			{
				"fields": ("is_active", "is_default", "created_at", "updated_at"),
			},
		),
	)

	def masked_api_key_display(self, obj):
		return obj.masked_api_key

	masked_api_key_display.short_description = "Resolved API key (masked)"


@admin.register(LLMModelConfig)
class LLMModelConfigAdmin(admin.ModelAdmin):
	list_display = (
		"name",
		"provider",
		"model_name",
		"tenant",
		"is_active",
		"is_default",
	)
	list_filter = ("is_active", "is_default", "tenant", "provider")
	search_fields = ("name", "slug", "model_name")
	readonly_fields = ("created_at", "updated_at")


@admin.register(EmbeddingModelConfig)
class EmbeddingModelConfigAdmin(admin.ModelAdmin):
	list_display = (
		"name",
		"provider",
		"model_name",
		"vector_size",
		"tenant",
		"is_active",
		"is_default",
	)
	list_filter = ("is_active", "is_default", "tenant", "provider")
	search_fields = ("name", "slug", "model_name")
	readonly_fields = ("created_at", "updated_at")
