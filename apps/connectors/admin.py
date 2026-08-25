from django.contrib import admin

from apps.connectors.models import ConnectorConfig, ConnectorRecord, ConnectorSyncRun


@admin.register(ConnectorConfig)
class ConnectorConfigAdmin(admin.ModelAdmin):
	list_display = ("name", "connector_type", "knowledge_base", "masked_token_display", "is_active")
	list_filter = ("connector_type", "is_active", "tenant")
	readonly_fields = ("masked_token_display",)

	def masked_token_display(self, obj):
		return obj.masked_token

	masked_token_display.short_description = "Resolved token (masked)"


@admin.register(ConnectorSyncRun)
class ConnectorSyncRunAdmin(admin.ModelAdmin):
	list_display = ("connector", "status", "fetched_count", "indexed_count", "created_at")
	list_filter = ("status", "connector__connector_type")


@admin.register(ConnectorRecord)
class ConnectorRecordAdmin(admin.ModelAdmin):
	list_display = ("connector", "external_id", "title", "is_active", "updated_at")
	search_fields = ("external_id", "title")
