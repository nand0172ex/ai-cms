from django.contrib import admin
from django.utils import timezone

from apps.ingestion.models import DataSource, IngestedChunk, IngestionJob, UploadedDocument


@admin.action(description="Mark selected jobs for retry")
def retry_jobs(modeladmin, request, queryset):
	queryset.update(status=IngestionJob.Status.PENDING, error_message="")


@admin.register(DataSource)
class DataSourceAdmin(admin.ModelAdmin):
	list_display = ("name", "source_type", "knowledge_base", "tenant", "is_active")
	list_filter = ("source_type", "is_active", "tenant")


@admin.register(UploadedDocument)
class UploadedDocumentAdmin(admin.ModelAdmin):
	list_display = ("title", "data_source", "file_type", "is_processed", "created_at")
	list_filter = ("file_type", "is_processed")
	search_fields = ("title", "checksum")


@admin.register(IngestionJob)
class IngestionJobAdmin(admin.ModelAdmin):
	list_display = ("id", "document", "status", "chunk_count", "started_at", "finished_at")
	list_filter = ("status",)
	actions = (retry_jobs,)

	@admin.action(description="Start selected pending jobs")
	def start_jobs(self, request, queryset):
		queryset.filter(status=IngestionJob.Status.PENDING).update(
			status=IngestionJob.Status.RUNNING,
			started_at=timezone.now(),
		)


@admin.register(IngestedChunk)
class IngestedChunkAdmin(admin.ModelAdmin):
	list_display = ("document", "knowledge_base", "chunk_index", "vector_id", "created_at")
	list_filter = ("knowledge_base",)
