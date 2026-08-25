# HANDOVER.md

This document is a factual snapshot of the project as it exists in the codebase right now.
It is written for another AI agent (or developer) to pick up work without needing prior chat history.
Everything here was verified by reading the actual files in the repository — nothing is assumed.

---

## 1. What This Project Is

A Django + Wagtail CMS project ("AI CMS") that combines:
- A Wagtail-powered content/admin backend
- A Retrieval-Augmented Generation (RAG) chat assistant
- A Qdrant vector database integration with a custom admin dashboard
- File upload / ingestion pipeline for building knowledge bases
- Multi-provider AI configuration (OpenAI, Gemini, Groq, Ollama, Local OpenAI-compatible)
- An "Embedding Profile" system for describing/testing embedding providers (informational layer, not yet wired into actual embedding computation)

Repository root: `/home/Nandprakash.Goutam1/Downloads/ai-cms`
Git: on branch `main`, working tree clean, latest commit `fb1da54` ("update-model").

---

## 2. Tech Stack (verified)

- Django `>=6,<6.1`, Wagtail `>=7.4,<7.5` (see `requirements.txt`)
- Database: SQLite by default (`db.sqlite3`, via `DATABASE_URL=sqlite:///db.sqlite3`); PostgreSQL supported via `dj_database_url` if `DATABASE_URL` is changed
- Redis + Celery configured (`django_celery_beat`, `django_celery_results`) for background tasks
- Qdrant Python client (`qdrant_client`) for vector storage
- `httpx` (v0.28.1 in this environment) used for provider connectivity checks
- LangChain (`langchain_openai`, `langchain_google_genai`) used for OpenAI/Gemini chat model construction
- Wagtail snippets/settings used heavily for admin-configurable data (no separate custom admin UI framework)

Settings module in use: `config/settings/base.py` (imported by `development.py` / `production.py`, not fully inspected but base is the source of truth for installed apps and most config).

---

## 3. Installed Apps (from `config/settings/base.py`)

```
apps.core
apps.accounts
apps.tenants
apps.branding
apps.navigation
apps.ai_providers
apps.prompts
apps.knowledge
apps.ingestion
apps.connectors
apps.retrieval
apps.workflows
apps.conversations
apps.audit
apps.observability
apps.api
home        (Wagtail default)
search      (Wagtail default)
```

Purpose of each (verified from models/views):

| App | Purpose |
|---|---|
| `core` | Shared `AbstractBaseModel` (created_at/updated_at) |
| `accounts` | Currently just re-declares an `AbstractBaseModel` copy; no custom user model found |
| `tenants` | `Tenant` model — logical multi-tenant boundary used as an optional FK across most models |
| `branding` | `BrandingSettings` Wagtail site setting (site name, tagline, logo, etc.) |
| `navigation` | `Menu` model for site navigation (Wagtail-orderable menu items) |
| `ai_providers` | `AIProviderConfig`, `LLMModelConfig`, `EmbeddingModelConfig`, `AIProviderSettings` (Wagtail setting) — defines OpenAI/Gemini/Groq/Ollama/Local providers and their models |
| `prompts` | `PromptTemplate` model (versioned prompt templates with draft/approved/archived status) |
| `knowledge` | **Core of the Qdrant integration.** `QdrantConnection`, `KnowledgeBase`, `EmbeddingProfile`, `VectorDBSettings` (Wagtail setting containing the whole custom "Qdrant Dashboard" UI) |
| `ingestion` | `DataSource`, `UploadedDocument`, `IngestionJob`, `IngestedChunk` + Celery task `process_ingestion_job` that extracts, chunks, and vectorizes documents into Qdrant |
| `connectors` | `ConnectorConfig` (Jira/Confluence), `ConnectorSyncRun`, `ConnectorRecord`, `ConnectorSettings` — external data source sync |
| `retrieval` | `RetrievalProfile` model + `RetrievalService` that queries Qdrant for relevant chunks |
| `workflows` | `RAGWorkflowService` — orchestrates retrieval + LLM call for chat responses |
| `conversations` | `AIAssistant`, `Conversation`, `Message`, `AssistantRuntimeSettings` — chat assistant configuration and the public-facing `/ai-assistant/` page |
| `audit` | `AuditEvent` model — append-only audit log used by dashboard "Recent Activities" |
| `observability` | `/health/`, `/ready/`, `/metrics/` endpoints |
| `api` | Public JSON API: `/api/v1/chat/`, `/api/v1/upload-file/`, `/api/v1/knowledge-bases/`, etc. |

---

## 4. URL Map (verified from `config/urls.py` and each app's `urls.py`)

```
/django-admin/                      Django admin
/admin/                             Wagtail admin
/settings/<path>/                   Redirects to /admin/settings/<path>/
/                                   Redirects to /ai-assistant/
/documents/                         Wagtail documents
/search/                            Wagtail search
/ai-assistant/                      apps.conversations.urls
/api/v1/chat/                       Chat endpoint (apps.api)
/api/v1/chat/stream/                Streaming chat (naive word-split streaming, not true token streaming)
/api/v1/upload-file/                File upload + ingestion trigger
/api/v1/conversations/              List recent conversations
/api/v1/assistants/                 List public active assistants
/api/v1/knowledge-bases/            List active knowledge bases
/api/v1/jobs/status/                Ingestion/connector job counters
/api/v1/errors/summary/             Recent audit "error" events
/api/v1/knowledge-bases/<slug>/stats/          Qdrant stats for one KB
/api/v1/vector-db/dashboard/                   Dashboard KPIs (used by Qdrant Dashboard UI)
/api/v1/vector-db/collections/                 GET list / POST create collection+KB
/api/v1/vector-db/collections/<slug>/          GET/PATCH/DELETE one collection
/api/v1/vector-db/uploads/status/              Recent ingestion job rows
/api/v1/vector-db/sync/status/                 Connector list + sync history
/api/v1/vector-db/sync/<id>/resync/            POST manual re-sync a connector
/api/v1/vector-db/embeddings/monitor/          Per-KB embedding metrics (chunk counts etc.)
/api/v1/vector-db/search-playground/           POST semantic search against Qdrant
/api/v1/vector-db/system-monitoring/           Connectivity, usage, growth, error logs
/api/v1/vector-db/connection/                  GET/POST Qdrant connection settings (test/save)
/api/v1/embedding-profiles/                    GET list of EmbeddingProfile cards
/api/v1/embedding-profiles/<slug>/connection/  POST test/save one embedding provider's connection
/health/, /ready/, /metrics/        Observability endpoints
```

The Wagtail settings page for the vector DB dashboard lives at:
`/admin/settings/knowledge/vectordbsettings/2/` (site-scoped Wagtail setting; the `2` is the site PK in this dev DB).

---

## 5. How The System Works (verified flows)

### 5.1 Chat flow (`apps/api/views.py::chat`)
1. Client POSTs `{prompt, assistant_slug?, conversation_id?}` to `/api/v1/chat/`.
2. Rate limiting via Django cache, keyed by session or IP, limit from `AssistantRuntimeSettings.max_requests_per_minute`.
3. Resolves an `AIAssistant` (by slug, or the configured default, or first active one).
4. Resolves an LLM model: `assistant.llm_model` or `AIProviderSettings.default_llm_model`.
5. **Strict restriction (verified in code):** only `ProviderType.OLLAMA` and `ProviderType.LOCAL_OPENAI` are allowed for chat. If the resolved model's provider is OpenAI/Gemini/Groq, the request is rejected with a 400 error. This means chat is **local-LLM-only by design** right now.
6. Resolves a `RetrievalProfile` (assistant's own, tenant default, or auto-creates one from `VectorDBSettings.default_knowledge_base`).
7. Calls `RAGWorkflowService().run(...)`.
8. `RAGWorkflowService`:
   - Retrieves chunks via `RetrievalService` (Qdrant-only, no DB fallback).
   - Builds a plain text prompt with retrieved context.
   - If the LLM provider is Ollama/Local OpenAI, calls it via raw `httpx.Client(trust_env=False)` POST to `/chat/completions` (bypasses LangChain entirely for these — this was done to fix proxy/connection issues seen earlier in this environment).
   - Otherwise uses `ProviderFactory.build_chat_model()` (LangChain) — but this path is effectively unreachable for chat today because of the local-only restriction above.
   - Raises `RuntimeError` on any failure (no silent fallback/demo text is generated) — the view catches this and returns HTTP 502 with the error message.
9. Saves `Message` rows (user + assistant), logs an `AuditEvent`.

### 5.2 Ingestion flow (`apps/api/views.py::upload_file` → `apps/ingestion/tasks.py::process_ingestion_job`)
1. Client POSTs multipart file to `/api/v1/upload-file/` with optional `knowledge_base_id`/`knowledge_base_slug`, `title`, `embedding_profile_slug`, `async`.
2. Resolves target `KnowledgeBase` (explicit → `VectorDBSettings.default_knowledge_base` → first active KB).
3. Creates `DataSource`, `UploadedDocument`, `IngestionJob`.
4. **`embedding_profile_slug` is recorded only as `document.metadata["embedding_profile"]`.** It does NOT change how vectors are computed (see 5.4 below — this was an explicit requirement).
5. If `async=true`, dispatches Celery task and returns 202 immediately; otherwise runs `process_ingestion_job` synchronously and returns the result.
6. `process_ingestion_job`:
   - Extracts text (`DocumentExtractionService`), splits into chunks (`ChunkingService`).
   - Deletes any previous `IngestedChunk` rows for the document, creates new ones.
   - Ensures the Qdrant collection exists (`CollectionManagementService.create_collection()`).
   - Builds Qdrant points using `text_to_vector()` (see 5.4) and upserts them via `QdrantRepository.upsert_points()`.
   - Updates job status/chunk_count.

### 5.3 Retrieval flow (`apps/retrieval/services.py`)
- `RetrievalService.retrieve()` is **Qdrant-only** — no relational-DB fallback exists (it was removed intentionally in an earlier iteration).
- Converts the query to a vector with the same `text_to_vector()` function, searches Qdrant, filters out non-human-readable text (binary/garbage detection heuristic), returns `{text, score, source, chunk_index}` list.
- On any Qdrant exception, returns `[]` (empty) rather than raising.

### 5.4 Vectorization — IMPORTANT, verified
`apps/knowledge/services/vectorizer.py::text_to_vector(text, size)` is a **deterministic SHA-256-hash-based vectorizer**. It is NOT a real embedding model. It is used everywhere today: ingestion, retrieval, and connector sync. This means:
- Semantic search quality is limited to hash-based similarity, not true semantic embeddings.
- The new `EmbeddingProfile` system (see below) is currently **informational/configuration only** — selecting HuggingFace/OpenAI/etc. as an embedding profile does not change this vectorizer. This was an explicit constraint given during implementation ("do not modify existing ingestion logic").

### 5.5 Qdrant Dashboard (the main admin UI built in this project)
Everything lives in **one file**: `apps/knowledge/models.py`, inside `VectorDBSettings.enterprise_dashboard_display` (a Python property that returns a huge string of HTML + CSS + vanilla JavaScript, rendered via a Wagtail `ReadOnlyPanel`).

- `VectorDBSettings` is a Wagtail site setting (`@register_setting`) with **exactly one panel**: `ReadOnlyPanel("enterprise_dashboard_display", heading="")`.
- The dashboard is a single-page app embedded directly in the Wagtail edit view: left sidebar navigation (Dashboard, Collections Management, Data Upload Center, Data Source Sync, Embedding Monitor, Search Playground, System Monitoring, Connection, User Help) + a main content area that swaps sections via `data-section` attributes and plain JS (`setActive()`), no framework.
- All data is fetched client-side via `fetch()` calls to the `/api/v1/vector-db/*` and `/api/v1/embedding-profiles/*` endpoints listed in section 4, using the Django session cookie + CSRF token read from `document.cookie`.
- Sidebar shows a live Qdrant connection status dot + a "Connection" tab where the Qdrant URL/API key/gRPC/timeout/default KB can be edited and tested without leaving the page.
- Backend logic for this dashboard lives in `apps/knowledge/services/dashboard_service.py` (`VectorDBDashboardService`) and `apps/knowledge/views.py`.

### 5.6 Embedding Profiles (new feature, verified)
- Model: `EmbeddingProfile` in `apps/knowledge/models.py`, registered as a **Wagtail snippet** (`@register_snippet`) — manageable at `/admin/snippets/knowledge/embeddingprofile/` without code changes.
- Fields: `name`, `slug`, `provider_type` (default/huggingface/openai/azure_openai/ollama/local/custom), `model_name`, `embedding_dimensions`, `best_use_case`, `performance_rating` (1–5), `cost_indicator` (free/low/medium/high), `capability` (online/offline/hybrid), `highlights` (JSON list of strings), `why_choose` (text), 5 boolean badge flags (recommended/cost_effective/fully_offline/fastest/highest_accuracy), `is_default`, `is_active`, `sort_order`.
- Connection fields (added later): `base_url`, `api_key`, `api_key_env_var`, `proxy_url` (optional), `connection_timeout_seconds`.
- `is_configured` property: `Default` type is always `True`; others require `base_url` set, and providers in `{openai, azure_openai, huggingface, custom}` also require an API key.
- `test_connection()`: sends a **POST** request (empty JSON body, `Content-Type: application/json`, optional `Authorization: Bearer <key>`, optional proxy) to `base_url`, with `trust_env=False` (ignores system proxy env vars unless one is explicitly configured). Returns `{available, detail, latency_ms, log}` where `log` is a list of human-readable trace lines (timestamps, method/url, proxy, auth, timeout, response/error) used to power the "Console" diagnostic panel in the UI.
- Seed data: 7 profiles (Default, HuggingFace, OpenAI, Azure OpenAI, Ollama Local, Local Models, Custom API) created via data migration `0005_seed_embedding_profiles.py`. Migration `0007` pre-fills a default `base_url` for the Ollama profile (`http://127.0.0.1:11434/v1/models`).
- Upload Center UI: shows one card per active profile with a green/red status dot (from `is_configured`, updated live after a test), badges, star rating, highlights, an expandable "Why choose this provider?" section, a "Configure" button (opens a modal with Base URL / API Key / **optional** Proxy URL / Timeout + Test Connection / Save / **Console** buttons), and a "Use this profile" button that sets the upload form's embedding-profile `<select>`. A "Compare Providers" button opens a modal with a full comparison table of all profiles.
- `apps/api/views.py::upload_file` reads the selected `embedding_profile_slug` and stores it as metadata (see 5.4 — does not affect actual vectorization).

---

## 6. Database / Migration History (knowledge app — most active app this session)

```
0001_initial.py                                  QdrantConnection, KnowledgeBase base schema
0002_knowledgebase_tenant_and_more.py             tenant scoping added
0003_qdrantconnection_api_key_vectordbsettings.py VectorDBSettings + api_key field added
0004_embeddingprofile_alter_vectordbsettings_options.py   EmbeddingProfile model created; VectorDBSettings Meta.verbose_name changed to "Qdrant Dashboard"
0005_seed_embedding_profiles.py                   Data migration: seeds the 7 default EmbeddingProfile rows
0006_embeddingprofile_api_key_and_more.py         Adds base_url, api_key, api_key_env_var, proxy_url, connection_timeout_seconds to EmbeddingProfile
0007_embedding_profile_connection_defaults.py     Data migration: sets Ollama profile's default base_url
```

All migrations have been applied to the local `db.sqlite3` (verified via `python manage.py migrate knowledge` output showing `OK` for each, and `python manage.py check` passes with 0 issues at time of writing).

No other app had migrations added/changed during this session (only `knowledge` was touched at the schema level).

---

## 7. Configuration (verified from `.env.example` and `config/settings/base.py`)

Environment variables read via `django-environ`:
```
DJANGO_SECRET_KEY, DJANGO_DEBUG (DEBUG), DJANGO_ALLOWED_HOSTS (ALLOWED_HOSTS)
DATABASE_URL              (default sqlite:///db.sqlite3)
REDIS_URL                 (default redis://localhost:6379/0)
CELERY_BROKER_URL, CELERY_RESULT_BACKEND
QDRANT_URL                (default http://localhost:6333)
QDRANT_API_KEY
OPENAI_API_KEY, GOOGLE_API_KEY, GOOGLE_GENAI_API_KEY, GROQ_API_KEY
OLLAMA_BASE_URL           (default http://localhost:11434)
LOCAL_OPENAI_BASE_URL     (default http://localhost:8000)
LOCAL_OPENAI_API_KEY
DEFAULT_TENANT_SLUG       (default "default")
FIELD_ENCRYPTION_KEY
LOG_LEVEL                 (default INFO)
```
Note: these are the *global process defaults*. The actual runtime Qdrant connection used by the dashboard/ingestion is stored per-site in the `VectorDBSettings` Wagtail model (DB-backed), not just env vars — the dashboard's "Connection" tab edits DB fields (`qdrant_url`, `qdrant_api_key`, `qdrant_prefer_grpc`, `qdrant_timeout_seconds`), which take precedence over env vars at runtime.

Similarly, `AIProviderSettings` (Wagtail setting in `apps.ai_providers`) stores DB-backed provider keys/URLs for OpenAI/Gemini/Groq/Ollama/Local OpenAI, separate from the `.env` values.

---

## 8. Features Confirmed Working (tested in this session via terminal + browser)

- Django system checks pass (`python manage.py check` → "System check identified no issues").
- Wagtail admin loads; `VectorDBSettings` page renders as a single "Qdrant Dashboard" panel (no duplicate/legacy field blocks).
- Qdrant Dashboard sidebar navigation switches sections client-side (buttons are `type="button"` with `preventDefault()`, so they no longer submit the Wagtail form — this was a real bug that was found and fixed).
- Dashboard KPI cards, Collections table, Upload Center, Data Source Sync, Embedding Monitor, Search Playground, System Monitoring, Connection tab, and Help section all fetch and render live data from the corresponding `/api/v1/vector-db/*` endpoints.
- Collection Create/Edit/Delete works through a real modal dialog (replaced earlier `window.prompt()`-based flow).
- File upload with drag-and-drop works; upload target collection is shown via a `<select>` (not a blind text field); ingestion job status list updates after upload.
- `/api/v1/embedding-profiles/` returns all 7 seeded profiles with correct `is_configured` flags (Default and Ollama = green/True in this environment; others red/False until configured).
- Embedding provider "Configure" modal: Test Connection and Save both work; proxy field confirmed to remain optional (empty string persists correctly, not required).
- Embedding provider "Console" button: confirmed to show a POST request trace (method, URL, proxy, masked auth header, timeout, response/error) for both HuggingFace and OpenAI test attempts.
- Chat endpoint correctly rejects non-local LLM providers with a clear error, and returns HTTP 502 with a real error message (not a fake/demo answer) when the local LLM or Qdrant is unreachable — verified via direct `Client().post()` calls in `manage.py shell`.
- Ollama-based chat was previously verified working end-to-end (model pulled: `llama3:8b`) when `ollama serve` was running locally in this environment; this is not guaranteed to still be running now.

---

## 9. Known Issues / Limitations (verified, not guesses)

1. **No internet access in this sandboxed environment.** Any embedding provider test against a real external host (OpenAI, HuggingFace, Azure) will fail with DNS/connect errors. This is an environment limitation, not a code bug — confirmed via direct `httpx` calls showing `[Errno -5] No address associated with hostname` and `ConnectTimeout`.
2. **Vectorization is not real embeddings.** `text_to_vector()` is a SHA-256 hash-based deterministic function, not a language-aware embedding model. Retrieval quality is limited by this.
3. **Embedding Profile selection is cosmetic today.** It is recorded on `UploadedDocument.metadata` but does not change which vectorizer/model actually runs. This was an explicit scope boundary set during implementation, not an oversight — but it should be flagged to any user expecting real multi-provider embeddings.
4. **Chat is hard-restricted to local LLM providers** (Ollama / Local OpenAI-compatible). OpenAI/Gemini/Groq configs exist in `apps.ai_providers` and have working LangChain adapters, but `apps/api/views.py::chat` explicitly blocks them for the chat endpoint.
5. **`RAGWorkflowService`'s LangChain path (`ProviderFactory.build_chat_model`) is effectively dead code for chat** given restriction #4 — it's only reachable if the local-only check is ever relaxed.
6. **Qdrant gRPC port (6334) may not be reachable** even when the HTTP port (6333) is — seen earlier as `grpc._channel._InactiveRpcError` / `Connection refused` on port 6334. The dashboard service was changed to force `prefer_grpc=False` for its own queries to avoid this, but other code paths (e.g. `QdrantRepository` default) may still default based on the `QdrantConnection.prefer_grpc` field, which is `False` by default.
7. **A `socksio` / SOCKS proxy warning** (`'socks5h' scheme not supported in proxy URI`) appears in logs when the Qdrant client initializes in this environment (proxy env vars set in the shell). It does not seem to block requests to `localhost` because `QdrantRepository._get_client()` explicitly adds `localhost`/`127.0.0.1`/`0.0.0.0` to `NO_PROXY` before creating the client.
8. **`chat_stream` endpoint is not true streaming** — it calls the normal `chat()` view synchronously, then fakes a stream by yielding `answer.split(" ")` word by word.
9. **The older `templates/conversations/chat_page.html`** (a separate, simpler upload/chat page under `/ai-assistant/assistants/<slug>/`) was NOT updated with the embedding profile selector or any of the Qdrant Dashboard work — it still has a plain file input. Only the Wagtail-admin "Qdrant Dashboard" upload center was enhanced.
10. **No automated tests were run/added for the new Qdrant Dashboard or Embedding Profile code** in this session beyond manual `manage.py shell` smoke tests and Playwright browser checks. Existing test files (`apps/knowledge/tests.py`, `apps/api/tests.py`) were not re-run as part of this work and may be stale relative to the current `apps/knowledge/services/repository.py` API (it gained `list_collections()` and `delete_collection()` methods that may not be covered by existing tests).
11. **The dashboard HTML/CSS/JS is a single large Python string** inside `apps/knowledge/models.py` (`enterprise_dashboard_display`, roughly 1300+ lines of the file). This is functional but hard to maintain — any future UI change requires care with Python string escaping (a real bug was hit and fixed earlier: JS `"\n"` inside the Python triple-quoted string was being interpreted as a literal newline by Python itself, breaking the JS; the fix was to use `"\\n"` in the Python source so the JS receives a literal `\n`). **Any future edit to this block must double-escape backslashes intended for JavaScript.**
12. **`.gitignore` was modified externally** just before this handover was written (noted by the environment as changed by "the user or possibly by a formatter"). Content of that change was not inspected as part of this handover — worth checking with `git log -p -- .gitignore` if it matters for next steps.

---

## 10. Pending Tasks (not started / explicitly deferred)

- Wire a real embedding model call behind the Embedding Profile selection (currently explicitly out of scope per user instruction: "Do not modify existing ingestion logic").
- Decide whether to relax or keep the "local LLM only" restriction on `/api/v1/chat/`.
- Add automated tests covering: `EmbeddingProfile.is_configured` / `test_connection()`, the new `/api/v1/vector-db/*` and `/api/v1/embedding-profiles/*` endpoints, and the collection create/edit/delete flow.
- Consider extracting the giant inline dashboard string in `apps/knowledge/models.py` into separate template/static files for maintainability (currently intentionally kept as one Python property for simplicity of the ReadOnlyPanel integration).
- Update `templates/conversations/chat_page.html` if the embedding profile / new upload UX should also apply there.
- Investigate and resolve the gRPC (port 6334) connectivity issue at the Qdrant deployment/network level if gRPC mode is ever required.
- Review `.gitignore` recent external change to confirm nothing important is now excluded from version control.

---

## 11. Exact Next Steps (recommended order)

1. Run `python manage.py check` and `python manage.py migrate` to confirm the environment is in the same state described here.
2. If continuing embedding-provider work: start from `apps/knowledge/models.py` → `EmbeddingProfile` class and `apps/knowledge/views.py` → `embedding_profiles` / `embedding_profile_connection` views.
3. If continuing dashboard UI work: the entire UI is inside `VectorDBSettings.enterprise_dashboard_display` in `apps/knowledge/models.py`. Search for `<div class="vdbx-shell"` to find the HTML start, and `<script>` near the end for the JS. Remember the double-backslash rule from section 9, item 11.
4. If continuing chat/LLM work: `apps/api/views.py::chat` and `apps/workflows/services.py::RAGWorkflowService` are the entry points. The local-only restriction is in `chat()` via `allowed_local_types = {ProviderType.OLLAMA, ProviderType.LOCAL_OPENAI}`.
5. Before testing chat or embedding connectivity live, confirm Qdrant is running (`curl http://localhost:6333/collections`) and, if testing local LLM chat, that Ollama is running (`ollama serve`) and the desired model is pulled (`ollama pull <model>`).
6. Always validate changes with:
   - `python manage.py check`
   - For any HTML string changes in `apps/knowledge/models.py`, extract and check the embedded `<script>` block with `node --check` (a working example command was used throughout this session: render the property via `manage.py shell`, split out the `<script>...</script>` section, and pipe to `node --check`).
