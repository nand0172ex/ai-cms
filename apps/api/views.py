import json
import time
from urllib.parse import urlparse

import httpx
from django.core.cache import cache
from django.http import JsonResponse
from django.http import StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from apps.accounts.models import UserEmbeddingCredential
from apps.audit.models import AuditEvent
from apps.ai_providers.models import AIProviderSettings
from apps.conversations.models import AssistantRuntimeSettings
from apps.conversations.models import AIAssistant, Conversation, Message
from apps.connectors.models import ConnectorSyncRun
from apps.ingestion.models import DataSource, IngestionJob, UploadedDocument
from apps.ingestion.tasks import process_ingestion_job
from apps.knowledge.models import EmbeddingProfile, KnowledgeBase, QdrantConnection, VectorDBSettings
from apps.knowledge.services.repository import QdrantRepository
from apps.retrieval.models import RetrievalProfile
from apps.workflows.services import RAGWorkflowService


@csrf_exempt
@require_POST
def chat(request):
	try:
		body = json.loads(request.body.decode("utf-8"))
	except Exception:
		return JsonResponse({"error": "Invalid JSON payload"}, status=400)

	prompt = (body.get("prompt") or "").strip()
	assistant_slug = body.get("assistant_slug")
	debug_enabled = bool(body.get("debug"))
	debug_info = {"stage": "request_received"} if debug_enabled else None
	if not prompt:
		return JsonResponse({"error": "prompt is required"}, status=400)

	runtime_settings = AssistantRuntimeSettings.for_request(request)
	client_key = request.session.session_key or request.META.get("REMOTE_ADDR", "anon")
	rate_key = f"chat-rate:{client_key}"
	current = cache.get(rate_key, 0)
	if current >= runtime_settings.max_requests_per_minute:
		return JsonResponse({"error": "rate limit exceeded"}, status=429)
	cache.set(rate_key, current + 1, 60)

	if not runtime_settings.allow_anonymous_chat and not request.user.is_authenticated:
		return JsonResponse({"error": "authentication required"}, status=403)

	assistant = AIAssistant.objects.filter(slug=assistant_slug, is_active=True).first()
	if not assistant:
		if runtime_settings.default_assistant_id:
			assistant = runtime_settings.default_assistant
		else:
			assistant = AIAssistant.objects.filter(is_active=True).first()
	if not assistant:
		return JsonResponse({"error": "No active assistant configured"}, status=400)

	conversation_id = body.get("conversation_id")
	conversation = None
	if conversation_id:
		conversation = Conversation.objects.filter(id=conversation_id, assistant=assistant).first()
	if not conversation:
		conversation = Conversation.objects.create(assistant=assistant, user=request.user if request.user.is_authenticated else None)

	Message.objects.create(conversation=conversation, role=Message.Role.USER, content=prompt)

	provider_settings = AIProviderSettings.for_request(request)
	resolved_reasoning_profile = provider_settings.get_active_reasoning_profile()
	resolved_llm_model = assistant.llm_model or provider_settings.default_llm_model
	resolved_retrieval_profile = assistant.retrieval_profile

	if not resolved_retrieval_profile:
		profile_qs = RetrievalProfile.objects
		if assistant.tenant_id:
			profile_qs = profile_qs.filter(tenant=assistant.tenant)
		else:
			profile_qs = profile_qs.filter(tenant__isnull=True)
		resolved_retrieval_profile = profile_qs.filter(is_default=True).first() or profile_qs.first()

	if not resolved_retrieval_profile:
		default_kb = VectorDBSettings.for_request(request).default_knowledge_base
		if default_kb:
			resolved_retrieval_profile = RetrievalProfile.objects.create(
				tenant=assistant.tenant,
				name=f"Auto Profile {default_kb.slug}",
				knowledge_base=default_kb,
				top_k=default_kb.top_k,
				similarity_threshold=default_kb.similarity_threshold,
				is_default=True,
			)

	if not resolved_retrieval_profile:
		return JsonResponse(
			{"error": "No retrieval profile/default knowledge base configured for Qdrant retrieval."},
			status=400,
		)

	if not resolved_reasoning_profile and not resolved_llm_model:
		return JsonResponse(
			{
				"error": "No reasoning provider configured. Set a default Reasoning Provider Profile in AI Provider settings.",
			},
			status=400,
		)

	try:
		if debug_info is not None:
			debug_info["stage"] = "workflow"
			debug_info["started_at"] = time.time()
		run = RAGWorkflowService().run(
			query=prompt,
			prompt_template=assistant.system_prompt,
			retrieval_profile=resolved_retrieval_profile,
			tenant=assistant.tenant,
			llm_model_config=resolved_llm_model,
			reasoning_profile=resolved_reasoning_profile,
			diagnostics=debug_info,
		)
	except RuntimeError as exc:
		payload = {"error": str(exc)}
		if debug_info is not None:
			debug_info["stage"] = debug_info.get("stage") or "failed"
			debug_info["error"] = str(exc)
			payload["debug"] = debug_info
		return JsonResponse(payload, status=502)

	Message.objects.create(
		conversation=conversation,
		role=Message.Role.ASSISTANT,
		content=run.response_text,
		citations=run.citations,
	)

	AuditEvent.objects.create(
		tenant=assistant.tenant,
		actor=request.user if request.user.is_authenticated else None,
		action="chat.request",
		resource_type="conversation",
		resource_id=str(conversation.id),
		metadata={"assistant": assistant.slug},
	)

	response_payload = {
		"conversation_id": conversation.id,
		"assistant": assistant.slug,
		"answer": run.response_text,
		"citations": run.citations,
	}
	if debug_info is not None:
		response_payload["debug"] = debug_info
	return JsonResponse(response_payload)


@csrf_exempt
@require_POST
def chat_stream(request):
	response = chat(request)
	if response.status_code != 200:
		return response

	payload = json.loads(response.content.decode("utf-8"))
	answer = payload.get("answer", "")

	def event_stream():
		for token in answer.split(" "):
			yield f"data: {token}\n\n"
		yield "data: [DONE]\n\n"

	return StreamingHttpResponse(event_stream(), content_type="text/event-stream")


@require_GET
def conversations(request):
	qs = Conversation.objects.order_by("-updated_at")[:50]
	data = [
		{
			"id": c.id,
			"assistant": c.assistant.slug,
			"title": c.title,
			"updated_at": c.updated_at.isoformat(),
		}
		for c in qs
	]
	return JsonResponse({"results": data})


@require_GET
def assistants(request):
	qs = AIAssistant.objects.filter(is_active=True, is_public=True).order_by("name")
	data = [
		{
			"name": a.name,
			"slug": a.slug,
			"description": a.description,
		}
		for a in qs
	]
	return JsonResponse({"results": data})


@require_GET
def knowledge_bases(request):
	qs = KnowledgeBase.objects.filter(is_active=True).order_by("name")
	data = [
		{
			"name": kb.name,
			"slug": kb.slug,
			"collection": kb.effective_collection_name,
			"document_count": kb.document_count,
		}
		for kb in qs
	]
	return JsonResponse({"results": data})


@require_GET
def job_status(request):
	return JsonResponse(
		{
			"ingestion": {
				"pending": IngestionJob.objects.filter(status=IngestionJob.Status.PENDING).count(),
				"running": IngestionJob.objects.filter(status=IngestionJob.Status.RUNNING).count(),
				"failed": IngestionJob.objects.filter(status=IngestionJob.Status.FAILED).count(),
			},
			"connectors": {
				"pending": ConnectorSyncRun.objects.filter(status=ConnectorSyncRun.Status.PENDING).count(),
				"running": ConnectorSyncRun.objects.filter(status=ConnectorSyncRun.Status.RUNNING).count(),
				"failed": ConnectorSyncRun.objects.filter(status=ConnectorSyncRun.Status.FAILED).count(),
			},
		}
	)


@require_GET
def runtime_health(request):
	provider_settings = AIProviderSettings.for_request(request)
	vector_settings = VectorDBSettings.for_request(request)

	qdrant = {
		"status": "unavailable",
		"url": vector_settings.qdrant_url or "http://localhost:6333",
		"latency_ms": None,
		"error": "",
	}

	try:
		temp_conn = QdrantConnection(
			url=qdrant["url"],
			api_key=vector_settings.qdrant_api_key or "",
			prefer_grpc=vector_settings.qdrant_prefer_grpc,
			timeout_seconds=vector_settings.qdrant_timeout_seconds or 30,
		)
		repo = QdrantRepository(temp_conn)
		started = time.perf_counter()
		repo.ping()
		qdrant["status"] = "connected"
		qdrant["latency_ms"] = int((time.perf_counter() - started) * 1000)
	except Exception as exc:
		qdrant["error"] = str(exc)

	ollama_url = (provider_settings.ollama_base_url or "http://127.0.0.1:11434/v1").strip().rstrip("/")
	if ollama_url.endswith("/v1"):
		ollama_url = ollama_url[: -len("/v1")]
	ollama_tags_url = f"{ollama_url}/api/tags"
	hostname = (urlparse(ollama_tags_url).hostname or "").lower()
	trust_env = hostname not in {"localhost", "127.0.0.1", "0.0.0.0"}

	ollama = {
		"status": "unavailable",
		"url": ollama_tags_url,
		"latency_ms": None,
		"error": "",
		"models": [],
	}

	try:
		started = time.perf_counter()
		with httpx.Client(timeout=5, trust_env=trust_env) as client:
			response = client.get(ollama_tags_url)
		ollama["latency_ms"] = int((time.perf_counter() - started) * 1000)
		if response.status_code < 500:
			payload = response.json() if response.content else {}
			models = payload.get("models") or []
			ollama["models"] = [item.get("name") for item in models if item.get("name")]
			ollama["status"] = "connected"
		else:
			ollama["error"] = f"HTTP {response.status_code}"
	except Exception as exc:
		ollama["error"] = str(exc)

	return JsonResponse({"qdrant": qdrant, "ollama": ollama})


@require_GET
def error_summary(request):
	errors = AuditEvent.objects.filter(action__icontains="error").order_by("-created_at")[:50]
	return JsonResponse(
		{
			"count": errors.count(),
			"results": [
				{
					"id": item.id,
					"action": item.action,
					"resource_type": item.resource_type,
					"resource_id": item.resource_id,
					"created_at": item.created_at.isoformat(),
				}
				for item in errors
			],
		}
	)


@csrf_exempt
@require_POST
def upload_file(request):
	uploaded_file = request.FILES.get("file")
	if not uploaded_file:
		return JsonResponse({"error": "file is required (multipart form-data)"}, status=400)

	knowledge_base = None
	knowledge_base_id = (request.POST.get("knowledge_base_id") or "").strip()
	knowledge_base_slug = (request.POST.get("knowledge_base_slug") or "").strip()

	active_kb_qs = KnowledgeBase.objects.filter(is_active=True)
	if knowledge_base_id:
		knowledge_base = active_kb_qs.filter(id=knowledge_base_id).first()
	if not knowledge_base and knowledge_base_slug:
		knowledge_base = active_kb_qs.filter(slug=knowledge_base_slug).first()

	if not knowledge_base:
		default_kb = VectorDBSettings.for_request(request).default_knowledge_base
		if default_kb and default_kb.is_active:
			knowledge_base = default_kb
	if not knowledge_base:
		knowledge_base = active_kb_qs.first()

	if not knowledge_base:
		return JsonResponse(
			{"error": "No active knowledge base found. Create one in admin first."},
			status=400,
		)

	title = (request.POST.get("title") or uploaded_file.name).strip() or uploaded_file.name

	# Optional: record which embedding profile the uploader picked. This is purely
	# informational metadata today and does not alter embedding/ingestion behavior.
	provider_settings = AIProviderSettings.for_request(request)
	embedding_profile_slug = (request.POST.get("embedding_profile_slug") or "").strip()
	embedding_profile = None
	if provider_settings.enable_embedding_profiles and embedding_profile_slug:
		embedding_profile = EmbeddingProfile.objects.filter(
			slug=embedding_profile_slug, is_active=True
		).first()
	if provider_settings.enable_embedding_profiles and not embedding_profile:
		embedding_profile = EmbeddingProfile.objects.filter(is_default=True, is_active=True).first()

	data_source = DataSource.objects.create(
		tenant=knowledge_base.tenant,
		knowledge_base=knowledge_base,
		name=f"Upload - {uploaded_file.name}",
		source_type=DataSource.SourceType.UPLOAD,
		config={
			"filename": uploaded_file.name,
			"size": uploaded_file.size,
			"content_type": uploaded_file.content_type or "",
		},
	)
	document = UploadedDocument.objects.create(
		tenant=knowledge_base.tenant,
		data_source=data_source,
		title=title,
		file=uploaded_file,
		metadata={
			"original_filename": uploaded_file.name,
			"content_type": uploaded_file.content_type or "",
			"embedding_profile": embedding_profile.slug if embedding_profile else "",
		},
	)
	job = IngestionJob.objects.create(
		document=document,
		created_by=request.user if request.user.is_authenticated else None,
		embedding_credential=(
			UserEmbeddingCredential.objects.filter(
				user=request.user, embedding_profile=embedding_profile, is_active=True
			).first()
			if request.user.is_authenticated
			and embedding_profile
			and embedding_profile.provider_type != EmbeddingProfile.ProviderType.DEFAULT
			else None
		),
	)

	run_async = (request.POST.get("async") or "false").lower() in {"1", "true", "yes"}
	if run_async:
		process_ingestion_job.delay(job.id)
		return JsonResponse(
			{
				"job_id": job.id,
				"document_id": document.id,
				"knowledge_base": knowledge_base.slug,
				"status": IngestionJob.Status.PENDING,
				"embedding_profile": embedding_profile.slug if embedding_profile else "",
			},
			status=202,
		)

	try:
		process_ingestion_job(job.id)
	except Exception:
		job.refresh_from_db(fields=["status", "error_message"])
		return JsonResponse(
			{
				"job_id": job.id,
				"document_id": document.id,
				"knowledge_base": knowledge_base.slug,
				"status": job.status,
				"error": job.error_message or "Failed to process document",
			},
			status=500,
		)

	job.refresh_from_db(fields=["status", "chunk_count"])
	return JsonResponse(
		{
			"job_id": job.id,
			"document_id": document.id,
			"knowledge_base": knowledge_base.slug,
			"status": job.status,
			"chunk_count": job.chunk_count,
			"embedding_profile": embedding_profile.slug if embedding_profile else "",
		},
		status=200,
	)
