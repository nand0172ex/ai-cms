from django.contrib import admin

from apps.retrieval.models import RetrievalProfile


@admin.register(RetrievalProfile)
class RetrievalProfileAdmin(admin.ModelAdmin):
	list_display = ("name", "knowledge_base", "top_k", "similarity_threshold", "is_default")
	list_filter = ("tenant", "is_default", "use_reranking")
