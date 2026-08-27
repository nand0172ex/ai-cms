import time

import httpx

from apps.ai_providers.models import ProviderType
from apps.ai_providers.models import ReasoningProviderProfile
from apps.workflows.models import WorkflowRun
from apps.retrieval.services import RetrievalService
from apps.ai_providers.services import ProviderFactory


class RAGWorkflowService:
    """Small, deterministic Phase 7 workflow scaffold."""

    @staticmethod
    def _is_local_qwen3_profile(profile):
        if not profile:
            return False
        if profile.provider_type != ReasoningProviderProfile.ProviderType.OLLAMA:
            return False
        return (profile.model_name or "").strip().lower().startswith("qwen3")

    def _effective_max_tokens(self, profile):
        max_tokens = int(profile.max_tokens or 256)
        if self._is_local_qwen3_profile(profile):
            # Keep local qwen3 response budgets modest for low-memory CPUs.
            return max(64, min(max_tokens, 256))
        return max_tokens

    def _build_retrieval_context(self, retrieved, reasoning_profile):
        chunks = [item.get("text", "") for item in retrieved[:3]]
        if self._is_local_qwen3_profile(reasoning_profile):
            # Trim context aggressively to avoid long decode times on local qwen3.
            chunks = [chunk[:900] for chunk in chunks]
        return "\n".join(chunks)

    @staticmethod
    def _openai_style_base_url(endpoint_url):
        if not endpoint_url:
            return ""
        base = endpoint_url.strip().rstrip("/")
        if base.endswith("/models"):
            base = base[: -len("/models")]
        return base

    def _precheck_ollama_runtime(self, profile, base_url):
        health_base = base_url.rstrip("/")
        if health_base.endswith("/v1"):
            health_base = health_base[: -len("/v1")]
        health_url = f"{health_base}/api/tags"
        try:
            with httpx.Client(trust_env=False, timeout=min(5, profile.timeout_seconds or 5)) as client:
                response = client.get(health_url)
        except Exception as exc:
            raise RuntimeError(
                f"Ollama precheck failed at {health_url}: {type(exc).__name__}: {exc}"
            ) from exc

        if response.status_code >= 400:
            raise RuntimeError(
                f"Ollama precheck failed at {health_url}: HTTP {response.status_code}"
            )

    def _invoke_reasoning_profile(self, profile, prompt):
        provider_type = profile.provider_type
        if provider_type == ReasoningProviderProfile.ProviderType.GEMINI:
            return self._invoke_reasoning_gemini(profile, prompt)
        return self._invoke_reasoning_openai_style(profile, prompt)

    def _invoke_reasoning_openai_style(self, profile, prompt):
        base_url = self._openai_style_base_url(profile.effective_endpoint_url())
        if not base_url:
            raise RuntimeError("Reasoning provider endpoint URL is missing.")

        if profile.provider_type == ReasoningProviderProfile.ProviderType.OLLAMA:
            self._precheck_ollama_runtime(profile, base_url)

        api_key = profile.get_api_key()
        if not api_key and profile.provider_type == ReasoningProviderProfile.ProviderType.OLLAMA:
            api_key = "ollama"

        payload = {
            "model": profile.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": profile.temperature,
            "max_tokens": self._effective_max_tokens(profile),
            "top_p": profile.top_p,
        }
        headers = {"Content-Type": "application/json", **(profile.headers or {})}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        trust_env = profile.provider_type not in {
            ReasoningProviderProfile.ProviderType.OLLAMA,
            ReasoningProviderProfile.ProviderType.OPENAI_COMPATIBLE,
        }
        response = None
        errors = []
        timeout_seconds = int(profile.timeout_seconds or 60)
        max_timeout_seconds = max(timeout_seconds, 300)

        # Connection refused often means local service warm-up/restart race.
        # Retry quickly with backoff before moving to timeout-oriented retries.
        refused_backoff = [0.25, 0.6]
        for wait_seconds in refused_backoff:
            try:
                with httpx.Client(trust_env=trust_env, timeout=timeout_seconds) as client:
                    response = client.post(
                        f"{base_url}/chat/completions", headers=headers, json=payload
                    )
                break
            except httpx.ConnectError as exc:
                errors.append(str(exc))
                err_msg = str(exc).lower()
                if "connection refused" in err_msg or "errno 111" in err_msg:
                    time.sleep(wait_seconds)
                    continue
                break
            except httpx.ReadTimeout as exc:
                errors.append(str(exc))
                break

        # Separate timeout retry path with extended timeout budget.
        if response is None:
            try:
                with httpx.Client(trust_env=trust_env, timeout=max_timeout_seconds) as client:
                    response = client.post(
                        f"{base_url}/chat/completions", headers=headers, json=payload
                    )
            except (httpx.ReadTimeout, httpx.ConnectError) as exc:
                errors.append(str(exc))

        if response is None:
            joined = " | ".join(errors) if errors else "unknown transport error"
            raise RuntimeError(f"Reasoning provider request failed: {joined}")

        if response.status_code >= 400:
            raise RuntimeError(
                f"Reasoning provider returned {response.status_code}: {response.text[:300]}"
            )

        data = response.json()
        message = data.get("choices", [{}])[0].get("message", {})
        content = (message.get("content") or "").strip()
        if content:
            return content

        # Qwen/Ollama may return reasoning text with empty final content.
        reasoning = (message.get("reasoning") or "").strip()
        if reasoning:
            return reasoning

        return ""

    def _invoke_reasoning_gemini(self, profile, prompt):
        api_key = profile.get_api_key()
        if not api_key:
            raise RuntimeError("Gemini API key is required for selected reasoning profile.")

        base_url = profile.effective_endpoint_url().rstrip("/")
        endpoint = f"{base_url}/models/{profile.model_name}:generateContent"
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": profile.temperature,
                "topP": profile.top_p,
                "maxOutputTokens": profile.max_tokens,
            },
        }
        headers = {"Content-Type": "application/json", **(profile.headers or {})}
        params = {"key": api_key}

        with httpx.Client(trust_env=True, timeout=profile.timeout_seconds) as client:
            response = client.post(endpoint, headers=headers, params=params, json=payload)

        if response.status_code >= 400:
            raise RuntimeError(
                f"Gemini provider returned {response.status_code}: {response.text[:300]}"
            )

        data = response.json()
        candidates = data.get("candidates") or []
        parts = (((candidates[0] or {}).get("content") or {}).get("parts") or []) if candidates else []
        text_chunks = [part.get("text", "") for part in parts if isinstance(part, dict)]
        return "\n".join([chunk for chunk in text_chunks if chunk]).strip()

    @staticmethod
    def _invoke_local_openai_compatible(llm_model_config, prompt):
        provider = llm_model_config.provider
        base_url = provider.base_url or ""
        if provider.provider_type == ProviderType.OLLAMA and not base_url:
            base_url = "http://127.0.0.1:11434/v1"
        if provider.provider_type == ProviderType.LOCAL_OPENAI and not base_url:
            base_url = "http://127.0.0.1:8001/v1"
        base_url = base_url.replace("http://localhost", "http://127.0.0.1")
        base_url = base_url.replace("https://localhost", "https://127.0.0.1")

        api_key = provider.get_api_key()
        if not api_key and provider.provider_type == ProviderType.OLLAMA:
            api_key = "ollama"
        if not api_key and provider.provider_type == ProviderType.LOCAL_OPENAI:
            api_key = "local-dev-key"

        payload = {
            "model": llm_model_config.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": llm_model_config.temperature,
            "max_tokens": llm_model_config.max_tokens,
            "top_p": llm_model_config.top_p,
            "frequency_penalty": llm_model_config.frequency_penalty,
            "presence_penalty": llm_model_config.presence_penalty,
            **(llm_model_config.model_kwargs or {}),
        }

        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        with httpx.Client(trust_env=False, timeout=provider.timeout_seconds) as client:
            response = client.post(f"{base_url.rstrip('/')}/chat/completions", headers=headers, json=payload)

        if response.status_code >= 400:
            raise RuntimeError(f"Local provider returned {response.status_code}: {response.text[:300]}")

        data = response.json()
        return (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
        )

    def run(
        self,
        query,
        prompt_template=None,
        retrieval_profile=None,
        tenant=None,
        llm_model_config=None,
        reasoning_profile=None,
        diagnostics=None,
    ):
        started_at = time.monotonic()
        if diagnostics is not None:
            diagnostics.update(
                {
                    "stage": "init",
                    "retrieval_status": "not_started",
                    "llm_status": "not_started",
                }
            )

        run = WorkflowRun.objects.create(
            tenant=tenant,
            prompt_template=prompt_template,
            retrieval_profile=retrieval_profile,
            query=query,
            rewritten_query=query.strip(),
        )
        context_prefix = ""
        if prompt_template:
            context_prefix = prompt_template.render({"query": query}) + "\n\n"

        retrieved = []
        if retrieval_profile:
            retrieval_diag = {} if diagnostics is not None else None
            if diagnostics is not None:
                diagnostics["stage"] = "retrieval"
            retrieved = RetrievalService().retrieve(
                retrieval_profile,
                query,
                diagnostics=retrieval_diag,
            )
            if diagnostics is not None:
                diagnostics["retrieval_status"] = "ok"
                diagnostics["retrieval_count"] = len(retrieved)
                diagnostics["retrieval"] = retrieval_diag or {}
        context_block = self._build_retrieval_context(retrieved, reasoning_profile)

        prompt = (
            f"{context_prefix}"
            "You are an AI issue triage assistant. Use retrieval context when present. "
            "If context is insufficient, state assumptions clearly.\n\n"
            f"Query:\n{query}\n\n"
            f"Retrieved Context:\n{context_block or 'No retrieval context available.'}\n"
        )

        if not reasoning_profile and not llm_model_config:
            raise RuntimeError("No LLM model configuration provided for strict live generation.")

        try:
            if diagnostics is not None:
                diagnostics["stage"] = "llm"
                if reasoning_profile:
                    diagnostics["llm_provider_type"] = reasoning_profile.provider_type
                    diagnostics["llm_model"] = reasoning_profile.model_name
                    diagnostics["llm_endpoint"] = reasoning_profile.effective_endpoint_url()
                elif llm_model_config:
                    diagnostics["llm_provider_type"] = llm_model_config.provider.provider_type
                    diagnostics["llm_model"] = llm_model_config.model_name
                    diagnostics["llm_endpoint"] = llm_model_config.provider.base_url or ""
            if reasoning_profile:
                response = self._invoke_reasoning_profile(reasoning_profile, prompt)
            else:
                provider_type = llm_model_config.provider.provider_type
                if provider_type in {ProviderType.OLLAMA, ProviderType.LOCAL_OPENAI}:
                    response = self._invoke_local_openai_compatible(llm_model_config, prompt)
                else:
                    chat_model = ProviderFactory.build_chat_model(llm_model_config)
                    llm_response = chat_model.invoke(prompt)
                    response = getattr(llm_response, "content", str(llm_response)).strip()
            if diagnostics is not None:
                diagnostics["llm_status"] = "ok"
        except Exception as exc:
            if diagnostics is not None:
                diagnostics["llm_status"] = "error"
                diagnostics["llm_error_type"] = exc.__class__.__name__
                diagnostics["llm_error"] = str(exc)
                diagnostics["elapsed_ms"] = int((time.monotonic() - started_at) * 1000)
            raise RuntimeError(f"LLM invocation failed: {exc}") from exc

        if not response:
            if diagnostics is not None:
                diagnostics["llm_status"] = "error"
                diagnostics["llm_error_type"] = "EmptyResponse"
                diagnostics["llm_error"] = "Local LLM returned an empty response."
                diagnostics["elapsed_ms"] = int((time.monotonic() - started_at) * 1000)
            raise RuntimeError("Local LLM returned an empty response.")

        run.response_text = response
        run.citations = [
            {"source": item.get("source"), "chunk_index": item.get("chunk_index"), "score": item.get("score")}
            for item in retrieved
        ]
        run.status = WorkflowRun.Status.SUCCESS
        run.save(update_fields=["response_text", "citations", "status", "updated_at"])
        if diagnostics is not None:
            diagnostics["stage"] = "completed"
            diagnostics["elapsed_ms"] = int((time.monotonic() - started_at) * 1000)
        return run
