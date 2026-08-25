import json

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET, require_http_methods

from apps.connectors.models import ConnectorConfig
from apps.knowledge.models import EmbeddingProfile
from apps.knowledge.models import KnowledgeBase
from apps.knowledge.models import VectorDBSettings
from apps.knowledge.services import CollectionManagementService
from apps.knowledge.services import VectorDBDashboardService


def _parse_json(request: HttpRequest):
	if not request.body:
		return {}
	try:
		return json.loads(request.body.decode("utf-8"))
	except Exception:
		return None


@login_required
@require_GET
def knowledge_base_collection_stats(request, slug):
	"""Return Qdrant collection statistics for a knowledge base."""

	kb = get_object_or_404(KnowledgeBase, slug=slug)
	stats = CollectionManagementService(kb).refresh_stats()
	payload = {
		"knowledge_base": kb.slug,
		"collection": kb.effective_collection_name,
		"stats": stats,
	}
	return JsonResponse(payload)


@login_required
@require_GET
def vector_db_dashboard(request):
	settings = VectorDBSettings.for_request(request)
	service = VectorDBDashboardService(settings)
	return JsonResponse({"dashboard": service.dashboard_overview()})


@login_required
@require_http_methods(["GET", "POST"])
def vector_db_collections(request):
	settings = VectorDBSettings.for_request(request)
	service = VectorDBDashboardService(settings)

	if request.method == "GET":
		try:
			return JsonResponse({"results": service.collections_summary()})
		except Exception as exc:
			return JsonResponse({"error": str(exc)}, status=503)

	body = _parse_json(request)
	if body is None:
		return JsonResponse({"error": "Invalid JSON payload"}, status=400)

	name = (body.get("name") or "").strip()
	slug = (body.get("slug") or "").strip()
	if not name:
		return JsonResponse({"error": "name is required"}, status=400)

	kb = KnowledgeBase.objects.create(
		tenant=None,
		qdrant_connection=settings.default_qdrant_connection,
		name=name,
		slug=slug or "",
		description=(body.get("description") or "").strip(),
		collection_name=(body.get("collection_name") or "").strip(),
		vector_size=int(body.get("vector_size") or 1536),
		top_k=int(body.get("top_k") or 5),
		similarity_threshold=float(body.get("similarity_threshold") or 0.7),
		is_active=True,
	)
	try:
		action = service.create_collection_for_kb(kb)
	except Exception as exc:
		kb.delete()
		return JsonResponse({"error": str(exc)}, status=503)
	return JsonResponse(
		{
			"created": True,
			"knowledge_base": kb.slug,
			"collection": kb.effective_collection_name,
			"collection_created": action["created"],
			"stats": action["stats"],
		},
		status=201,
	)


@login_required
@require_http_methods(["GET", "PATCH", "DELETE"])
def vector_db_collection_detail(request, slug):
	kb = get_object_or_404(KnowledgeBase, slug=slug)
	settings = VectorDBSettings.for_request(request)
	service = VectorDBDashboardService(settings)

	if request.method == "GET":
		try:
			stats = CollectionManagementService(kb).refresh_stats()
		except Exception as exc:
			return JsonResponse({"error": str(exc)}, status=503)
		return JsonResponse(
			{
				"knowledge_base": kb.slug,
				"name": kb.name,
				"collection": kb.effective_collection_name,
				"vector_size": kb.vector_size,
				"top_k": kb.top_k,
				"similarity_threshold": kb.similarity_threshold,
				"stats": stats,
			}
		)

	if request.method == "PATCH":
		body = _parse_json(request)
		if body is None:
			return JsonResponse({"error": "Invalid JSON payload"}, status=400)
		for field in ["name", "description", "top_k", "similarity_threshold", "is_active"]:
			if field in body:
				setattr(kb, field, body[field])
		if "vector_size" in body:
			kb.vector_size = int(body["vector_size"])
		kb.save()
		try:
			stats = CollectionManagementService(kb).refresh_stats()
		except Exception as exc:
			return JsonResponse({"error": str(exc)}, status=503)
		return JsonResponse({"updated": True, "knowledge_base": kb.slug, "stats": stats})

	try:
		result = service.delete_collection_for_kb(kb)
	except Exception as exc:
		return JsonResponse({"error": str(exc)}, status=503)
	kb.delete()
	return JsonResponse({"deleted": True, **result})


@login_required
@require_GET
def vector_db_upload_status(request):
	settings = VectorDBSettings.for_request(request)
	service = VectorDBDashboardService(settings)
	return JsonResponse({"results": service.uploads_status()})


@login_required
@require_GET
def vector_db_sync_status(request):
	settings = VectorDBSettings.for_request(request)
	service = VectorDBDashboardService(settings)
	return JsonResponse(
		{
			"connectors": service.connector_summary(),
			"sync_history": service.sync_status(),
		}
	)


@login_required
@require_http_methods(["POST"])
def vector_db_manual_resync(request, connector_id):
	connector = get_object_or_404(ConnectorConfig, id=connector_id)
	settings = VectorDBSettings.for_request(request)
	service = VectorDBDashboardService(settings)
	try:
		payload = service.trigger_manual_resync(connector)
	except Exception as exc:
		return JsonResponse({"error": str(exc)}, status=503)
	return JsonResponse(payload)


@login_required
@require_GET
def vector_db_embedding_monitor(request):
	settings = VectorDBSettings.for_request(request)
	service = VectorDBDashboardService(settings)
	return JsonResponse({"results": service.embedding_monitor()})


@login_required
@require_http_methods(["POST"])
def vector_db_search_playground(request):
	body = _parse_json(request)
	if body is None:
		return JsonResponse({"error": "Invalid JSON payload"}, status=400)

	query = (body.get("query") or "").strip()
	kb_slug = (body.get("knowledge_base_slug") or "").strip()
	if not query:
		return JsonResponse({"error": "query is required"}, status=400)

	kb = None
	if kb_slug:
		kb = KnowledgeBase.objects.filter(slug=kb_slug, is_active=True).first()
	if not kb:
		kb = VectorDBSettings.for_request(request).default_knowledge_base
	if not kb:
		kb = KnowledgeBase.objects.filter(is_active=True).first()
	if not kb:
		return JsonResponse({"error": "No active knowledge base found"}, status=400)

	top_k = int(body.get("top_k") or kb.top_k or 5)
	score_threshold = body.get("score_threshold")
	score_threshold = float(score_threshold) if score_threshold is not None else None

	settings = VectorDBSettings.for_request(request)
	service = VectorDBDashboardService(settings)
	try:
		results = service.search_playground(kb=kb, query=query, top_k=top_k, score_threshold=score_threshold)
	except Exception as exc:
		return JsonResponse({"error": str(exc)}, status=503)
	return JsonResponse(
		{
			"knowledge_base": kb.slug,
			"collection": kb.effective_collection_name,
			"query": query,
			"results": results,
		}
	)


@login_required
@require_GET
def vector_db_system_monitoring(request):
	settings = VectorDBSettings.for_request(request)
	service = VectorDBDashboardService(settings)
	return JsonResponse({"monitoring": service.system_monitoring()})


@require_GET
def embedding_profiles(request):
	"""List configurable embedding provider profiles for the upload UI.

	This is informational only: selecting a profile does not change how
	chunks are embedded today. New providers can be added by staff via the
	Embedding Profile snippet without any code or frontend changes.
	"""

	profiles = EmbeddingProfile.objects.filter(is_active=True).order_by("sort_order", "name")
	default_profile = profiles.filter(is_default=True).first()
	return JsonResponse(
		{
			"results": [profile.to_card_dict() for profile in profiles],
			"default_slug": default_profile.slug if default_profile else "",
		}
	)


@login_required
@require_http_methods(["POST"])
def embedding_profile_connection(request, slug):
	"""Test or save the connection settings for a single embedding provider.

	Proxy URL is always optional. Sending "save": true persists the fields;
	otherwise the values are only used for a one-off connectivity test.
	"""

	profile = get_object_or_404(EmbeddingProfile, slug=slug)
	body = _parse_json(request)
	if body is None:
		return JsonResponse({"error": "Invalid JSON payload"}, status=400)

	base_url = body.get("base_url")
	api_key = (body.get("api_key") or "").strip() or None
	proxy_url = body.get("proxy_url")
	timeout_seconds = body.get("connection_timeout_seconds")
	try:
		timeout_seconds = int(timeout_seconds) if timeout_seconds not in (None, "") else None
	except (TypeError, ValueError):
		timeout_seconds = None

	result = profile.test_connection(
		base_url=base_url,
		api_key=api_key,
		proxy_url=proxy_url,
		timeout_seconds=timeout_seconds,
	)

	if body.get("save"):
		if base_url is not None:
			profile.base_url = (base_url or "").strip()
		if api_key:
			profile.api_key = api_key
		if proxy_url is not None:
			profile.proxy_url = (proxy_url or "").strip()
		if timeout_seconds:
			profile.connection_timeout_seconds = timeout_seconds
		profile.save()
		result["saved"] = True
	else:
		result["saved"] = False

	result["profile"] = profile.to_card_dict()
	return JsonResponse(result)


@login_required
@require_http_methods(["GET", "POST"])
def vector_db_connection(request):
	"""Inspect or update the active Qdrant connection used by the dashboard."""

	settings = VectorDBSettings.for_request(request)

	if request.method == "POST":
		body = _parse_json(request)
		if body is None:
			return JsonResponse({"error": "Invalid JSON payload"}, status=400)

		if "qdrant_url" in body:
			url = (body.get("qdrant_url") or "").strip()
			if url:
				settings.qdrant_url = url
		if body.get("qdrant_api_key"):
			settings.qdrant_api_key = body.get("qdrant_api_key").strip()
		if "qdrant_prefer_grpc" in body:
			settings.qdrant_prefer_grpc = bool(body.get("qdrant_prefer_grpc"))
		if "qdrant_timeout_seconds" in body:
			try:
				settings.qdrant_timeout_seconds = int(body.get("qdrant_timeout_seconds") or 30)
			except (TypeError, ValueError):
				pass
		if "default_knowledge_base_slug" in body:
			slug = (body.get("default_knowledge_base_slug") or "").strip()
			settings.default_knowledge_base = (
				KnowledgeBase.objects.filter(slug=slug).first() if slug else None
			)
		settings.save()

	result = settings.get_test_connection()
	return JsonResponse(
		{
			"qdrant_url": settings.qdrant_url,
			"qdrant_api_key_set": bool(settings.qdrant_api_key),
			"qdrant_prefer_grpc": settings.qdrant_prefer_grpc,
			"qdrant_timeout_seconds": settings.qdrant_timeout_seconds,
			"default_knowledge_base_slug": (
				settings.default_knowledge_base.slug if settings.default_knowledge_base_id else ""
			),
			"connected": result["connected"],
			"error": result["error"],
			"collections_found": len(result["collections"]),
		}
	)
