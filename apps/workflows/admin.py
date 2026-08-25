from django.contrib import admin

from apps.workflows.models import WorkflowRun


@admin.register(WorkflowRun)
class WorkflowRunAdmin(admin.ModelAdmin):
	list_display = ("id", "status", "tenant", "created_at")
	list_filter = ("status", "tenant")
	search_fields = ("query", "rewritten_query", "response_text")
