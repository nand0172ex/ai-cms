from django.contrib import admin
from django.utils import timezone

from apps.prompts.models import PromptTemplate


@admin.action(description="Approve selected templates")
def approve_templates(modeladmin, request, queryset):
	queryset.update(
		status=PromptTemplate.Status.APPROVED,
		approved_by=request.user,
		approved_at=timezone.now(),
	)


@admin.register(PromptTemplate)
class PromptTemplateAdmin(admin.ModelAdmin):
	list_display = ("key", "version", "tenant", "status", "approved_by", "updated_at")
	list_filter = ("tenant", "status")
	search_fields = ("key", "name", "slug", "template")
	actions = (approve_templates,)
