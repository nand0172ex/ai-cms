from django.contrib import admin
from django.contrib import messages
from django.utils.html import format_html

from apps.knowledge.models import KnowledgeBase, QdrantConnection
from apps.knowledge.services import CollectionManagementService, QdrantRepository


@admin.action(description="Test selected Qdrant connections")
def test_qdrant_connections(modeladmin, request, queryset):
	success_count = 0
	for connection in queryset:
		try:
			QdrantRepository(connection).ping()
			success_count += 1
		except Exception as exc:
			modeladmin.message_user(
				request,
				f"{connection.name}: {exc}",
				level=messages.ERROR,
			)

	if success_count:
		modeladmin.message_user(
			request,
			f"{success_count} connection(s) reachable.",
			level=messages.SUCCESS,
		)


@admin.register(QdrantConnection)
class QdrantConnectionAdmin(admin.ModelAdmin):
	list_display = (
		"name",
		"tenant",
		"url",
		"connection_status_badge",
		"collections_count_display",
		"is_active",
		"is_default",
	)
	list_filter = ("tenant", "is_active", "is_default", "prefer_grpc", "verify_tls")
	search_fields = ("name", "slug", "url", "api_key_env_var")
	readonly_fields = (
		"masked_api_key_display",
		"connection_status_display",
		"collections_list_display",
		"created_at",
		"updated_at",
	)
	actions = (test_qdrant_connections,)
	fieldsets = (
		(
			"Scope",
			{"fields": ("tenant", "name", "slug", "is_active", "is_default")},
		),
		(
			"Connection",
			{
				"fields": (
					"url",
					"api_key_env_var",
					"api_key",
					"masked_api_key_display",
					"prefer_grpc",
					"verify_tls",
					"timeout_seconds",
				)
			},
		),
		(
			"Status",
			{
				"fields": (
					"connection_status_display",
					"collections_list_display",
				)
			},
		),
	)

	def masked_api_key_display(self, obj):
		return obj.masked_api_key

	masked_api_key_display.short_description = "Resolved API key (masked)"

	def connection_status_badge(self, obj):
		try:
			QdrantRepository(obj).ping()
			return format_html('<span style="color: green;">● Connected</span>')
		except Exception:
			return format_html('<span style="color: red;">● Disconnected</span>')

	connection_status_badge.short_description = "Status"

	def connection_status_display(self, obj):
		try:
			QdrantRepository(obj).ping()
			return format_html('<span style="color: green; font-weight: bold;">✓ Connected</span>')
		except Exception as exc:
			return format_html(
				'<span style="color: red; font-weight: bold;">✗ Connection Failed</span><br><small>{}</small>',
				str(exc),
			)

	connection_status_display.short_description = "Connection Status"

	def collections_count_display(self, obj):
		try:
			repo = QdrantRepository(obj)
			collections = repo._get_client().get_collections().collections
			return len(collections)
		except Exception:
			return "-"

	collections_count_display.short_description = "Collections"

	def collections_list_display(self, obj):
		try:
			repo = QdrantRepository(obj)
			collections = repo._get_client().get_collections().collections
			if not collections:
				return format_html('<em>No collections found</em>')
			collection_items = "".join(
				[
					f"<li><strong>{c.name}</strong> - {getattr(c, 'points_count', 'N/A')} points</li>"
					for c in collections
				]
			)
			return format_html(f"<ul>{collection_items}</ul>")
		except Exception as exc:
			return format_html('<span style="color: red;">Error: {}</span>', str(exc))

	collections_list_display.short_description = "Collections in Qdrant"


@admin.action(description="Create collections for selected knowledge bases")
def create_qdrant_collections(modeladmin, request, queryset):
	created_count = 0
	existing_count = 0
	for kb in queryset:
		try:
			created = CollectionManagementService(kb).create_collection()
			if created:
				created_count += 1
			else:
				existing_count += 1
		except Exception as exc:
			modeladmin.message_user(request, f"{kb.name}: {exc}", level=messages.ERROR)

	if created_count:
		modeladmin.message_user(
			request,
			f"Created {created_count} collection(s).",
			level=messages.SUCCESS,
		)
	if existing_count:
		modeladmin.message_user(
			request,
			f"{existing_count} collection(s) already existed.",
			level=messages.WARNING,
		)


@admin.action(description="Validate collections for selected knowledge bases")
def validate_qdrant_collections(modeladmin, request, queryset):
	valid_count = 0
	for kb in queryset:
		try:
			exists = CollectionManagementService(kb).validate_collection()
			if exists:
				valid_count += 1
			else:
				modeladmin.message_user(
					request,
					f"{kb.name}: collection not found in Qdrant",
					level=messages.WARNING,
				)
		except Exception as exc:
			modeladmin.message_user(request, f"{kb.name}: {exc}", level=messages.ERROR)

	if valid_count:
		modeladmin.message_user(
			request,
			f"Validated {valid_count} collection(s).",
			level=messages.SUCCESS,
		)


@admin.action(description="Refresh collection stats for selected knowledge bases")
def refresh_collection_stats(modeladmin, request, queryset):
	refreshed = 0
	for kb in queryset:
		try:
			CollectionManagementService(kb).refresh_stats()
			refreshed += 1
		except Exception as exc:
			modeladmin.message_user(request, f"{kb.name}: {exc}", level=messages.ERROR)

	if refreshed:
		modeladmin.message_user(
			request,
			f"Refreshed stats for {refreshed} knowledge base(s).",
			level=messages.SUCCESS,
		)


@admin.register(KnowledgeBase)
class KnowledgeBaseAdmin(admin.ModelAdmin):
	list_display = (
		"name",
		"tenant",
		"qdrant_connection",
		"effective_collection_name",
		"collection_status_badge",
		"document_count",
		"is_active",
	)
	list_filter = ("tenant", "qdrant_connection", "is_active")
	search_fields = ("name", "slug", "collection_name")
	readonly_fields = (
		"effective_collection_name",
		"collection_status_display",
		"collection_stats_display",
		"created_at",
		"updated_at",
	)
	fieldsets = (
		(
			"Configuration",
			{
				"fields": (
					"tenant",
					"qdrant_connection",
					"name",
					"slug",
					"description",
					"collection_name",
					"effective_collection_name",
					"vector_size",
					"is_active",
				)
			},
		),
		(
			"Retrieval Configuration",
			{
				"fields": (
					"top_k",
					"similarity_threshold",
				)
			},
		),
		(
			"Qdrant Status",
			{
				"fields": (
					"collection_status_display",
					"collection_stats_display",
				)
			},
		),
	)
	actions = (
		create_qdrant_collections,
		validate_qdrant_collections,
		refresh_collection_stats,
	)

	def collection_status_badge(self, obj):
		try:
			exists = CollectionManagementService(obj).validate_collection()
			if exists:
				return format_html('<span style="color: green;">● Exists</span>')
			return format_html('<span style="color: orange;">● Not Found</span>')
		except Exception:
			return format_html('<span style="color: red;">● Error</span>')

	collection_status_badge.short_description = "Collection"

	def collection_status_display(self, obj):
		try:
			service = CollectionManagementService(obj)
			if service.validate_collection():
				return format_html(
					'<span style="color: green; font-weight: bold;">✓ Collection exists in Qdrant</span><br>'
					'<small>Collection: <code>{}</code></small>',
					obj.effective_collection_name,
				)
			return format_html(
				'<span style="color: orange; font-weight: bold;">⚠ Collection not found</span><br>'
				'<small>Expected: <code>{}</code></small>',
				obj.effective_collection_name,
			)
		except Exception as exc:
			return format_html(
				'<span style="color: red; font-weight: bold;">✗ Connection Error</span><br><small>{}</small>',
				str(exc),
			)

	collection_status_display.short_description = "Collection Status"

	def collection_stats_display(self, obj):
		try:
			stats = CollectionManagementService(obj).refresh_stats()
			return format_html(
				'<table style="width: 100%; border-collapse: collapse;">'
				'<tr><th style="text-align: left; padding: 4px;">Points Count:</th><td>{}</td></tr>'
				'<tr><th style="text-align: left; padding: 4px;">Vectors Count:</th><td>{}</td></tr>'
				'<tr><th style="text-align: left; padding: 4px;">Vector Size:</th><td>{}</td></tr>'
				'<tr><th style="text-align: left; padding: 4px;">Status:</th><td>{}</td></tr>'
				'</table>',
				stats.get("points_count", 0),
				stats.get("vectors_count", 0),
				stats.get("vector_size", "N/A"),
				stats.get("status", "unknown"),
			)
		except Exception as exc:
			return format_html('<span style="color: red;">Error: {}</span>', str(exc))

	collection_stats_display.short_description = "Collection Stats (Live)"
