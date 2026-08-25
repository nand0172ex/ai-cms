from django.contrib import admin

from apps.audit.models import AuditEvent


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
	list_display = ("created_at", "action", "resource_type", "resource_id", "actor", "tenant")
	list_filter = ("action", "resource_type", "tenant")
	search_fields = ("action", "resource_id", "correlation_id")
