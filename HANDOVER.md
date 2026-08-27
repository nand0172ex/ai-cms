# Handover Notes (Updated: 2026-08-27)

This handover is for another agent/developer continuing this project on a different system.
It reflects the current repository state and recent runtime hardening work.

## 1) Current Goal and Reality

- Primary issue observed here is local Ollama instability (intermittent connection refused), not retrieval logic.
- Retrieval to Qdrant is working and now explicitly traceable.
- The code now includes stage-level diagnostics to separate retrieval-stage vs LLM-stage failures.
- Commercial providers (OpenAI/Gemini) are configured in the architecture, but this environment cannot test them due to blocked external access.

## 2) Most Important Recent Changes

### 2.1 Chat diagnostics and stage tracing

Files:
- apps/api/views.py
- apps/workflows/services.py
- config/templates/ai_assistant_home.html

What changed:
- `/api/v1/chat/` now accepts optional `debug: true` in request body.
- When debug is enabled, response includes a `debug` object with:
  - `stage`
  - `retrieval_status`
  - `retrieval_count`
  - `retrieval` metadata (target collection, selected live collection, available collections)
  - `llm_status`
  - `llm_error_type`
  - `llm_error`
  - `elapsed_ms`
  - provider routing metadata (`llm_provider_type`, `llm_model`, `llm_endpoint`)
- Front page flow log (`/ai-assistant/`) now prints these debug fields.

### 2.2 Live collection guard for retrieval

File:
- apps/retrieval/services.py

What changed:
- Retrieval resolves a currently live Qdrant collection before querying.
- If configured collection is missing, it falls back to another active KB collection that exists.
- If none exist, retrieval returns empty results instead of querying a deleted collection.
- Diagnostics now expose:
  - target collection
  - selected collection
  - available collections

### 2.3 Ollama-specific hardening

File:
- apps/workflows/services.py

What changed:
- Added precheck for Ollama health before chat completion:
  - precheck URL is host-root `/api/tags` (strip trailing `/v1` first)
- Added targeted retry/backoff for connection-refused errors.
- Kept timeout retry path separate.
- Important: Ollama precheck is only for Ollama provider profiles.

### 2.4 Runtime health endpoint and admin badges

Files:
- apps/api/views.py
- apps/api/urls.py
- apps/ai_providers/models.py

What changed:
- Added `/api/v1/runtime-health/` returning independent health for:
  - qdrant: status/url/latency/error
  - ollama: status/url/latency/error/models
- AI Provider Settings page now has runtime badges:
  - Qdrant connected/unavailable
  - Ollama connected/unavailable (+ model count)
- Added manual `Refresh Runtime` button and periodic auto refresh.
- Verified in browser that badges render and refresh.

## 3) Verified Runtime Behavior In This Environment

- `python manage.py check` passes.
- `/api/v1/runtime-health/` returns 200 and independent service states.
- Typical failing chat result with debug enabled:
  - `stage = llm`
  - `retrieval_status = ok`
  - `llm_status = error`
  - `llm_provider_type = ollama`
  - error indicates Ollama connectivity (`ConnectError: [Errno 111] Connection refused`)

Interpretation:
- Qdrant path is healthy.
- Failure is LLM transport/runtime on local machine.

## 4) Why This Matters For Commercial Provider Switch

- The debug payload now proves which provider/model/endpoint is used per request.
- Once external access is available, switching active reasoning profile to OpenAI/Gemini can be validated immediately from logs without guessing.
- Ollama-only failures should not be mistaken for cloud provider failures because provider route is now explicit.

## 5) What To Test On A Different System (Internet Enabled)

### 5.1 Pre-flight

1. Run migrations and checks:
   - `python manage.py migrate`
   - `python manage.py check`
2. Ensure Qdrant is reachable.
3. Configure OpenAI/Gemini reasoning profile token and endpoint in admin snippets.

### 5.2 Provider switch verification

1. Go to AI Provider Settings.
2. Click `Use this profile` on Gemini or OpenAI profile.
3. Open `/ai-assistant/` and run Analyze.
4. Confirm flow log lines contain:
   - `provider=gemini` or `provider=openai`
   - cloud endpoint in `llm_endpoint`
   - no Ollama precheck/connect-refused message

### 5.3 API-level verification (recommended)

POST `/api/v1/chat/` with:
- `{"prompt": "reply only OK", "debug": true}`

Validate response:
- `debug.llm_provider_type` matches selected cloud provider
- `debug.llm_endpoint` matches expected cloud URL
- `status = 200` and non-empty `answer`

## 6) Known Limitations / Notes

- Current local environment cannot reliably validate external providers due to network restrictions.
- If cloud provider requests fail on another system, use `debug.llm_error_type` and `debug.llm_error` first before changing code.
- Frontend and admin behavior was modified carefully to avoid disturbing existing flows (save button behavior, profile activation, diagnostics visibility).

## 7) Quick File Map For Next Agent

- Chat API: apps/api/views.py
- Chat route table: apps/api/urls.py
- Workflow orchestration + provider invocation: apps/workflows/services.py
- Retrieval + collection resolution: apps/retrieval/services.py
- AI Provider admin UI rendering script: apps/ai_providers/models.py
- Front assistant page behavior: config/templates/ai_assistant_home.html
- Reasoning profile test/select APIs: apps/knowledge/views.py

## 8) Suggested Next Work (Not Implemented Yet)

1. Optional fallback provider chain (primary provider fails -> try configured backup provider).
2. Small circuit-breaker for repeated transport failures to reduce repeated 502 bursts.
3. Request ID correlation in chat responses and server logs for easier production incident tracing.
4. Optional pre-analyze runtime health ribbon on `/ai-assistant/`.

## 9) One-Line Summary

System is now instrumented to clearly separate retrieval success from LLM provider failures; local Ollama instability remains the active issue here, while cloud-provider routing and diagnostics are ready for validation on a network-enabled environment.
