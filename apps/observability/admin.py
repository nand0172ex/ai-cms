from django.contrib import admin

from apps.observability.models import HealthSnapshot


@admin.register(HealthSnapshot)
class HealthSnapshotAdmin(admin.ModelAdmin):
	list_display = ("component", "status", "created_at")
	list_filter = ("component", "status")
