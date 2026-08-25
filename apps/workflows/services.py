import httpx

from apps.ai_providers.models import ProviderType
from apps.workflows.models import WorkflowRun
from apps.retrieval.services import RetrievalService
from apps.ai_providers.services import ProviderFactory


class RAGWorkflowService:
    """Small, deterministic Phase 7 workflow scaffold."""

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

    def run(self, query, prompt_template=None, retrieval_profile=None, tenant=None, llm_model_config=None):
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
            retrieved = RetrievalService().retrieve(retrieval_profile, query)
        context_block = "\n".join([item["text"] for item in retrieved[:3]])

        prompt = (
            f"{context_prefix}"
            "You are an AI issue triage assistant. Use retrieval context when present. "
            "If context is insufficient, state assumptions clearly.\n\n"
            f"Query:\n{query}\n\n"
            f"Retrieved Context:\n{context_block or 'No retrieval context available.'}\n"
        )

        if not llm_model_config:
            raise RuntimeError("No LLM model configuration provided for strict live generation.")

        try:
            provider_type = llm_model_config.provider.provider_type
            if provider_type in {ProviderType.OLLAMA, ProviderType.LOCAL_OPENAI}:
                response = self._invoke_local_openai_compatible(llm_model_config, prompt)
            else:
                chat_model = ProviderFactory.build_chat_model(llm_model_config)
                llm_response = chat_model.invoke(prompt)
                response = getattr(llm_response, "content", str(llm_response)).strip()
        except Exception as exc:
            raise RuntimeError(f"Local LLM invocation failed: {exc}") from exc

        if not response:
            raise RuntimeError("Local LLM returned an empty response.")

        run.response_text = response
        run.citations = [
            {"source": item.get("source"), "chunk_index": item.get("chunk_index"), "score": item.get("score")}
            for item in retrieved
        ]
        run.status = WorkflowRun.Status.SUCCESS
        run.save(update_fields=["response_text", "citations", "status", "updated_at"])
        return run
