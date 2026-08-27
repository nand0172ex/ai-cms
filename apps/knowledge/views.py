import json

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET, require_http_methods

from apps.accounts.models import UserEmbeddingCredential
from apps.ai_providers.models import AIProviderSettings
from apps.ai_providers.models import ReasoningProviderProfile
from apps.connectors.models import ConnectorConfig
from apps.connectors.services import ConnectorRegistry
from apps.connectors.services import ConnectorSyncService
from apps.knowledge.models import EmbeddingProfile
from apps.knowledge.models import KnowledgeBase
from apps.knowledge.models import VectorDBSettings
from apps.knowledge.services import CollectionManagementService
from apps.knowledge.services import VectorDBDashboardService


def _can_view_vector_status(request):
	return request.user.is_superuser or request.user.has_perm("knowledge.view_knowledgebase")


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
	if not _can_view_vector_status(request):
		return JsonResponse({"error": "You do not have permission to view vector processing status."}, status=403)
	settings = VectorDBSettings.for_request(request)
	service = VectorDBDashboardService(settings)
	return JsonResponse(service.uploads_status(user=request.user))


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


def _connector_to_dict(connector):
	cfg = connector.config or {}
	embedding_slug = (cfg.get("embedding_profile_slug") or "").strip()
	embedding_profile = (
		EmbeddingProfile.objects.filter(slug=embedding_slug, is_active=True).only("name").first()
		if embedding_slug
		else None
	)
	return {
		"id": connector.id,
		"name": connector.name,
		"connector_type": connector.connector_type,
		"knowledge_base_slug": connector.knowledge_base.slug if connector.knowledge_base_id else "",
		"knowledge_base_name": connector.knowledge_base.name if connector.knowledge_base_id else "",
		"base_url": connector.base_url,
		"project_key": connector.project_key,
		"is_active": connector.is_active,
		"token_env_var": connector.token_env_var,
		"token_set": bool(connector.get_token()),
		"token_masked": connector.masked_token,
		"auth_type": cfg.get("auth_type") or "bearer",
		"sync_mode": cfg.get("sync_mode") or "incremental",
		"sync_interval_minutes": int(cfg.get("sync_interval_minutes") or 30),
		"proxy_url": cfg.get("proxy_url") or "",
		"embedding_profile_slug": embedding_slug,
		"embedding_profile_name": embedding_profile.name if embedding_profile else "",
		"last_cursor": cfg.get("last_cursor") or "",
		"last_sync_at": cfg.get("last_sync_at") or "",
		"timeout_seconds": cfg.get("timeout_seconds") or 30,
		"config": cfg,
	}


@login_required
@require_http_methods(["GET", "POST"])
def vector_db_connectors(request):
	if request.method == "GET":
		rows = list(
			ConnectorConfig.objects.select_related("knowledge_base")
			.order_by("name")
		)
		return JsonResponse({"results": [_connector_to_dict(item) for item in rows]})

	body = _parse_json(request)
	if body is None:
		return JsonResponse({"error": "Invalid JSON payload"}, status=400)

	name = (body.get("name") or "").strip()
	connector_type = (body.get("connector_type") or "rest_api").strip().lower()
	kb_slug = (body.get("knowledge_base_slug") or "").strip()
	base_url = (body.get("base_url") or "").strip()
	if not name:
		return JsonResponse({"error": "name is required"}, status=400)
	if not base_url:
		return JsonResponse({"error": "base_url is required"}, status=400)

	kb = KnowledgeBase.objects.filter(slug=kb_slug, is_active=True).first() if kb_slug else None
	if not kb:
		kb = VectorDBSettings.for_request(request).default_knowledge_base or KnowledgeBase.objects.filter(is_active=True).first()
	if not kb:
		return JsonResponse({"error": "No active knowledge base found."}, status=400)

	config = dict(body.get("config") or {})
	if "auth_type" in body:
		config["auth_type"] = (body.get("auth_type") or "bearer").strip().lower()
	if "sync_mode" in body:
		config["sync_mode"] = (body.get("sync_mode") or "incremental").strip().lower()
	if "timeout_seconds" in body:
		try:
			config["timeout_seconds"] = int(body.get("timeout_seconds") or 30)
		except (TypeError, ValueError):
			config["timeout_seconds"] = 30
	if "sync_interval_minutes" in body:
		try:
			interval = int(body.get("sync_interval_minutes") or 30)
		except (TypeError, ValueError):
			interval = 30
		config["sync_interval_minutes"] = 1440 if interval >= 1440 else 30
	if "proxy_url" in body:
		config["proxy_url"] = (body.get("proxy_url") or "").strip()
	if "embedding_profile_slug" in body:
		emb_slug = (body.get("embedding_profile_slug") or "").strip()
		if emb_slug:
			emb = EmbeddingProfile.objects.filter(slug=emb_slug, is_active=True).first()
			if not emb:
				return JsonResponse({"error": "Embedding profile not found."}, status=404)
			config["embedding_profile_slug"] = emb.slug
		else:
			config["embedding_profile_slug"] = ""

	connector = ConnectorConfig.objects.create(
		tenant=None,
		knowledge_base=kb,
		name=name,
		connector_type=connector_type,
		base_url=base_url,
		token_env_var=(body.get("token_env_var") or "").strip(),
		access_token=(body.get("access_token") or "").strip(),
		project_key=(body.get("project_key") or "").strip(),
		is_active=bool(body.get("is_active", True)),
		config=config,
	)
	return JsonResponse({"created": True, "connector": _connector_to_dict(connector)}, status=201)


@login_required
@require_http_methods(["GET", "PATCH", "DELETE"])
def vector_db_connector_detail(request, connector_id):
	connector = get_object_or_404(ConnectorConfig.objects.select_related("knowledge_base"), id=connector_id)
	if request.method == "GET":
		return JsonResponse({"connector": _connector_to_dict(connector)})

	if request.method == "DELETE":
		connector.delete()
		return JsonResponse({"deleted": True})

	body = _parse_json(request)
	if body is None:
		return JsonResponse({"error": "Invalid JSON payload"}, status=400)

	if "name" in body:
		connector.name = (body.get("name") or "").strip() or connector.name
	if "connector_type" in body:
		connector.connector_type = (body.get("connector_type") or connector.connector_type).strip().lower()
	if "base_url" in body:
		connector.base_url = (body.get("base_url") or "").strip() or connector.base_url
	if "project_key" in body:
		connector.project_key = (body.get("project_key") or "").strip()
	if "token_env_var" in body:
		connector.token_env_var = (body.get("token_env_var") or "").strip()
	if "access_token" in body and (body.get("access_token") or "").strip():
		connector.access_token = (body.get("access_token") or "").strip()
	if "is_active" in body:
		connector.is_active = bool(body.get("is_active"))
	if "knowledge_base_slug" in body:
		slug = (body.get("knowledge_base_slug") or "").strip()
		if slug:
			kb = KnowledgeBase.objects.filter(slug=slug, is_active=True).first()
			if not kb:
				return JsonResponse({"error": "Knowledge base not found."}, status=404)
			connector.knowledge_base = kb

	config = dict(connector.config or {})
	if "config" in body and isinstance(body.get("config"), dict):
		config.update(body.get("config") or {})
	if "auth_type" in body:
		config["auth_type"] = (body.get("auth_type") or "bearer").strip().lower()
	if "sync_mode" in body:
		config["sync_mode"] = (body.get("sync_mode") or "incremental").strip().lower()
	if "timeout_seconds" in body:
		try:
			config["timeout_seconds"] = int(body.get("timeout_seconds") or 30)
		except (TypeError, ValueError):
			pass
	if "sync_interval_minutes" in body:
		try:
			interval = int(body.get("sync_interval_minutes") or 30)
		except (TypeError, ValueError):
			interval = 30
		config["sync_interval_minutes"] = 1440 if interval >= 1440 else 30
	if "proxy_url" in body:
		config["proxy_url"] = (body.get("proxy_url") or "").strip()
	if "embedding_profile_slug" in body:
		emb_slug = (body.get("embedding_profile_slug") or "").strip()
		if emb_slug:
			emb = EmbeddingProfile.objects.filter(slug=emb_slug, is_active=True).first()
			if not emb:
				return JsonResponse({"error": "Embedding profile not found."}, status=404)
			config["embedding_profile_slug"] = emb.slug
		else:
			config["embedding_profile_slug"] = ""
	connector.config = config
	connector.save()
	return JsonResponse({"updated": True, "connector": _connector_to_dict(connector)})


@login_required
@require_http_methods(["POST"])
def vector_db_connector_test(request, connector_id):
	connector = get_object_or_404(ConnectorConfig, id=connector_id)
	cfg = connector.config or {}
	log = [
		f"[TEST] Source: {connector.name} ({connector.connector_type})",
		f"URL: {connector.base_url}",
		f"Auth: {cfg.get('auth_type') or 'bearer'}",
		f"Proxy: {cfg.get('proxy_url') or 'none'}",
		f"Timeout: {cfg.get('timeout_seconds') or 30}s",
	]
	try:
		client = ConnectorRegistry.get_client(connector)
		client.test_connection()
		log.append("Result: connection successful.")
		return JsonResponse({"available": True, "detail": "Connection successful.", "log": log})
	except Exception as exc:
		log.append("Result: connection failed.")
		log.append(f"Error: {str(exc)}")
		return JsonResponse({"available": False, "detail": str(exc), "error": str(exc), "log": log}, status=503)


@login_required
@require_http_methods(["POST"])
def vector_db_connector_sync(request, connector_id):
	connector = get_object_or_404(ConnectorConfig, id=connector_id)
	cfg = connector.config or {}
	log = [
		f"[SYNC] Source: {connector.name} ({connector.connector_type})",
		f"Mode: {cfg.get('sync_mode') or 'incremental'}",
		f"Interval: {cfg.get('sync_interval_minutes') or 30} minute(s)",
	]
	try:
		run = ConnectorSyncService().run_sync(connector)
		connector.refresh_from_db(fields=["config"])
		run_detail = run.error_message or "Sync completed."
		log.extend(
			[
				f"Run ID: {run.id}",
				f"Status: {run.status}",
				f"Fetched: {run.fetched_count}",
				f"Indexed: {run.indexed_count}",
				f"Last cursor: {(connector.config or {}).get('last_cursor') or '-'}",
				f"Last sync at: {(connector.config or {}).get('last_sync_at') or '-'}",
				f"Detail: {run_detail}",
			]
		)
		return JsonResponse(
			{
				"run_id": run.id,
				"status": run.status,
				"fetched_count": run.fetched_count,
				"indexed_count": run.indexed_count,
				"detail": run_detail,
				"log": log,
			}
		)
	except Exception as exc:
		log.append("Result: sync failed.")
		log.append(f"Error: {str(exc)}")
		return JsonResponse({"error": str(exc), "detail": str(exc), "log": log}, status=503)


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
	if not _can_view_vector_status(request):
		return JsonResponse({"error": "You do not have permission to view embedding status."}, status=403)
	settings = VectorDBSettings.for_request(request)
	service = VectorDBDashboardService(settings)
	return JsonResponse({"results": service.embedding_monitor(user=request.user)})


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


@login_required
@require_GET
def embedding_profiles(request):
	"""List configurable embedding provider profiles for the upload UI.

	This is informational only: selecting a profile does not change how
	chunks are embedded today. New providers can be added by staff via the
	Embedding Profile snippet without any code or frontend changes.
	"""

	provider_settings = AIProviderSettings.for_request(request)
	if not provider_settings.enable_embedding_profiles:
		return JsonResponse(
			{
				"enabled": False,
				"results": [],
				"default_slug": "",
				"message": "Embedding profiles are disabled by AI Provider settings.",
			}
		)

	scope = (request.GET.get("scope") or "dashboard").strip().lower()
	profiles_qs = EmbeddingProfile.objects.filter(is_active=True)
	if scope != "settings":
		profiles_qs = profiles_qs.filter(show_on_dashboard=True)
	profiles = profiles_qs.order_by("sort_order", "name")
	default_profile = profiles.filter(is_default=True).first()
	results = []
	for profile in profiles:
		card = profile.to_card_dict()
		if profile.provider_type != EmbeddingProfile.ProviderType.DEFAULT:
			credential = UserEmbeddingCredential.objects.filter(
				user=request.user, embedding_profile=profile, is_active=True
			).first()
			card["api_key_set"] = bool(credential and credential.encrypted_api_key)
			card["api_key_masked"] = credential.masked_api_key if credential else ""
			card["is_configured"] = profile.is_configured_for_user(request.user)
		results.append(card)
	return JsonResponse(
		{
			"enabled": True,
			"results": results,
			"default_slug": default_profile.slug if default_profile else "",
		}
	)


@login_required
@require_http_methods(["GET", "POST"])
def embedding_profile_connection(request, slug):
	"""Test or save the connection settings for a single embedding provider.

	Proxy URL is always optional. Sending "save": true persists the fields;
	otherwise the values are only used for a one-off connectivity test.
	"""

	provider_settings = AIProviderSettings.for_request(request)
	if not provider_settings.enable_embedding_profiles:
		return JsonResponse(
			{"error": "Embedding profiles are disabled in AI Provider settings."},
			status=403,
		)

	profile = get_object_or_404(EmbeddingProfile, slug=slug, is_active=True, show_on_dashboard=True)
	body = _parse_json(request) if request.method == "POST" else {}
	if body is None:
		return JsonResponse({"error": "Invalid JSON payload"}, status=400)
	if request.method == "GET":
		body = {
			"base_url": request.headers.get("X-Embedding-Base-Url"),
			"api_key": request.headers.get("X-Embedding-Api-Key"),
			"proxy_url": request.headers.get("X-Embedding-Proxy-Url"),
			"connection_timeout_seconds": request.headers.get("X-Embedding-Timeout"),
		}
	if profile.provider_type != EmbeddingProfile.ProviderType.DEFAULT:
		credential = UserEmbeddingCredential.objects.filter(
			user=request.user, embedding_profile=profile, is_active=True
		).first()
	else:
		credential = None

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
		api_key=api_key or (credential.get_api_key() if credential else None),
		proxy_url=proxy_url,
		timeout_seconds=timeout_seconds,
		user=request.user,
	)

	if request.method == "POST" and body.get("save"):
		if base_url is not None:
			profile.base_url = (base_url or "").strip()
		if profile.provider_type != EmbeddingProfile.ProviderType.DEFAULT and api_key:
			credential, _ = UserEmbeddingCredential.objects.get_or_create(
				user=request.user, embedding_profile=profile,
				defaults={"is_active": True},
			)
			credential.set_api_key(api_key)
			credential.is_active = True
			credential.save(update_fields=["encrypted_api_key", "is_active", "updated_at"])
		elif api_key:
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
	if profile.provider_type != EmbeddingProfile.ProviderType.DEFAULT:
		credential = UserEmbeddingCredential.objects.filter(
			user=request.user, embedding_profile=profile, is_active=True
		).first()
		result["profile"]["api_key_set"] = bool(credential and credential.encrypted_api_key)
		result["profile"]["api_key_masked"] = credential.masked_api_key if credential else ""
	return JsonResponse(result)


@login_required
@require_GET
def reasoning_profiles(request):
	"""List reasoning provider profiles for dashboard admin cards."""

	provider_settings = AIProviderSettings.for_request(request)
	if not provider_settings.enable_reasoning_profiles:
		return JsonResponse(
			{
				"enabled": False,
				"results": [],
				"default_slug": "",
				"message": "Reasoning provider profiles are disabled by AI Provider settings.",
			}
		)

	scope = (request.GET.get("scope") or "dashboard").strip().lower()
	profiles_qs = ReasoningProviderProfile.objects.filter(is_active=True)
	if scope != "settings":
		profiles_qs = profiles_qs.filter(show_on_dashboard=True)
	profiles = profiles_qs.order_by("sort_order", "name")
	selected = provider_settings.get_active_reasoning_profile()
	results = []
	for profile in profiles:
		card = profile.to_card_dict()
		card["is_selected"] = bool(selected and selected.pk == profile.pk)
		results.append(card)
	return JsonResponse(
		{
			"enabled": True,
			"results": results,
			"default_slug": selected.slug if selected else "",
		}
	)


@login_required
@require_http_methods(["POST"])
def reasoning_profile_connection(request, slug):
	"""Test/save/select one reasoning provider profile from dashboard modal."""

	provider_settings = AIProviderSettings.for_request(request)
	if not provider_settings.enable_reasoning_profiles:
		return JsonResponse(
			{"error": "Reasoning provider profiles are disabled in AI Provider settings."},
			status=403,
		)

	profile = get_object_or_404(ReasoningProviderProfile, slug=slug, is_active=True, show_on_dashboard=True)
	body = _parse_json(request)
	if body is None:
		return JsonResponse({"error": "Invalid JSON payload"}, status=400)

	endpoint_url = body.get("endpoint_url")
	model_name = (body.get("model_name") or "").strip() or None
	api_key = (body.get("api_key") or "").strip() or None
	timeout_seconds = body.get("timeout_seconds")
	try:
		timeout_seconds = int(timeout_seconds) if timeout_seconds not in (None, "") else None
	except (TypeError, ValueError):
		timeout_seconds = None

	result = profile.test_connection(
		endpoint_url=endpoint_url,
		api_key=api_key,
		timeout_seconds=timeout_seconds,
	)

	if body.get("save"):
		if endpoint_url is not None:
			profile.endpoint_url = (endpoint_url or "").strip()
		if model_name:
			profile.model_name = model_name
		if api_key:
			profile.api_key = api_key
		if timeout_seconds:
			profile.timeout_seconds = timeout_seconds
		profile.save()
		result["saved"] = True
	else:
		result["saved"] = False

	if body.get("set_default"):
		ReasoningProviderProfile.objects.filter(is_default=True).exclude(pk=profile.pk).update(is_default=False)
		if not profile.is_default:
			profile.is_default = True
			profile.save(update_fields=["is_default", "updated_at"])

		runtime_type = AIProviderSettings._reasoning_to_runtime_type(profile.provider_type)
		provider_settings.default_reasoning_profile = profile
		provider_settings.active_provider_type = runtime_type
		provider_settings.save(update_fields=["default_reasoning_profile", "active_provider_type"])
		result["selected"] = True
	else:
		result["selected"] = False

	result["profile"] = profile.to_card_dict()
	result["default_slug"] = (
		provider_settings.default_reasoning_profile.slug if provider_settings.default_reasoning_profile_id else ""
	)
	return JsonResponse(result)


@login_required
@require_http_methods(["GET", "POST"])
def reasoning_profile_settings(request):
	"""Read or update reasoning provider controller settings for AI settings UI."""

	provider_settings = AIProviderSettings.for_request(request)

	if request.method == "POST":
		body = _parse_json(request)
		if body is None:
			return JsonResponse({"error": "Invalid JSON payload"}, status=400)

		if "enable_reasoning_profiles" in body:
			provider_settings.enable_reasoning_profiles = bool(body.get("enable_reasoning_profiles"))

		if "enable_embedding_profiles" in body:
			provider_settings.enable_embedding_profiles = bool(body.get("enable_embedding_profiles"))

		if "default_reasoning_profile_slug" in body:
			slug = (body.get("default_reasoning_profile_slug") or "").strip()
			if slug:
				profile = ReasoningProviderProfile.objects.filter(
					slug=slug,
					is_active=True,
					show_on_dashboard=True,
				).first()
				if not profile:
					return JsonResponse({"error": "Reasoning profile not found or not visible."}, status=404)
				provider_settings.default_reasoning_profile = profile
				provider_settings.active_provider_type = AIProviderSettings._reasoning_to_runtime_type(
					profile.provider_type
				)
			else:
				provider_settings.default_reasoning_profile = None

		provider_settings.save()

	active = provider_settings.get_active_reasoning_profile()
	return JsonResponse(
		{
			"enable_reasoning_profiles": provider_settings.enable_reasoning_profiles,
			"enable_embedding_profiles": provider_settings.enable_embedding_profiles,
			"active_provider_type": provider_settings.active_provider_type,
			"active_provider_display": provider_settings.get_active_provider_type_display(),
			"default_reasoning_profile_slug": active.slug if active else "",
			"default_reasoning_profile_name": active.name if active else "",
		}
	)


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
