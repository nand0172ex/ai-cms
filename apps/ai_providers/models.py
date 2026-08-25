import os
from urllib.parse import urlparse

import httpx
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.text import slugify
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.contrib.settings.models import BaseSiteSetting, register_setting

from apps.core.models import AbstractBaseModel
from apps.knowledge.panels import ReadOnlyPanel


class ProviderType(models.TextChoices):
    OPENAI = "openai", "OpenAI"
    GEMINI = "gemini", "Google Gemini"
    GROQ = "groq", "Groq"
    OLLAMA = "ollama", "Ollama"
    LOCAL_OPENAI = "local_openai", "Local OpenAI-Compatible"


class AIProviderConfig(AbstractBaseModel):
    """Top-level provider credentials and connection options."""

    tenant = models.ForeignKey(
        "tenants.Tenant",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="ai_providers",
        help_text="Optional tenant scope. Leave empty for global provider.",
    )
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140)
    provider_type = models.CharField(max_length=32, choices=ProviderType.choices)

    base_url = models.URLField(blank=True)
    api_key_env_var = models.CharField(
        max_length=120,
        blank=True,
        help_text="Environment variable name that stores the provider API key.",
    )
    api_key = models.CharField(
        max_length=255,
        blank=True,
        help_text="Optional direct API key for zero-touch admin setup.",
    )
    headers = models.JSONField(default=dict, blank=True)
    timeout_seconds = models.PositiveIntegerField(default=60)

    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]
        unique_together = [("tenant", "slug")]
        verbose_name = "AI Provider"
        verbose_name_plural = "AI Providers"

    def __str__(self):
        scope = self.tenant.slug if self.tenant_id else "global"
        return f"{self.name} ({scope})"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        key_required = self.provider_type in {
            ProviderType.OPENAI,
            ProviderType.GEMINI,
            ProviderType.GROQ,
        }
        if key_required and not self.api_key_env_var and not self.api_key:
            raise ValidationError(
                {
                    "api_key_env_var": "Provide either api_key_env_var or api_key for this provider."
                }
            )

        if self.is_default:
            qs = AIProviderConfig.objects.filter(is_default=True)
            if self.tenant_id:
                qs = qs.filter(tenant=self.tenant)
            else:
                qs = qs.filter(tenant__isnull=True)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                raise ValidationError(
                    {"is_default": "Only one default provider is allowed per scope."}
                )

    def get_api_key(self):
        if self.api_key:
            return self.api_key
        if not self.api_key_env_var:
            return ""
        return os.getenv(self.api_key_env_var, "")

    @property
    def masked_api_key(self):
        key = self.get_api_key()
        if not key:
            return "(missing)"
        visible = key[-4:] if len(key) >= 4 else key
        return f"{'*' * max(0, len(key) - len(visible))}{visible}"


class LLMModelConfig(AbstractBaseModel):
    """LLM model configuration bound to a provider."""

    tenant = models.ForeignKey(
        "tenants.Tenant",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="llm_models",
    )
    provider = models.ForeignKey(
        AIProviderConfig,
        on_delete=models.CASCADE,
        related_name="llm_models",
    )
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140)
    model_name = models.CharField(max_length=160)

    temperature = models.FloatField(default=0.2)
    max_tokens = models.PositiveIntegerField(default=1024)
    top_p = models.FloatField(default=1.0)
    frequency_penalty = models.FloatField(default=0.0)
    presence_penalty = models.FloatField(default=0.0)
    supports_streaming = models.BooleanField(default=True)

    model_kwargs = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]
        unique_together = [("tenant", "slug"), ("provider", "model_name")]
        verbose_name = "LLM Model"
        verbose_name_plural = "LLM Models"

    def __str__(self):
        return f"{self.name} ({self.model_name})"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        if self.is_default:
            qs = LLMModelConfig.objects.filter(is_default=True)
            if self.tenant_id:
                qs = qs.filter(tenant=self.tenant)
            else:
                qs = qs.filter(tenant__isnull=True)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                raise ValidationError(
                    {"is_default": "Only one default LLM model is allowed per scope."}
                )


class EmbeddingModelConfig(AbstractBaseModel):
    """Embedding model configuration for ingestion and retrieval."""

    tenant = models.ForeignKey(
        "tenants.Tenant",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="embedding_models",
    )
    provider = models.ForeignKey(
        AIProviderConfig,
        on_delete=models.CASCADE,
        related_name="embedding_models",
    )
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140)
    model_name = models.CharField(max_length=160)
    vector_size = models.PositiveIntegerField(default=1536)
    batch_size = models.PositiveIntegerField(default=32)

    model_kwargs = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]
        unique_together = [("tenant", "slug"), ("provider", "model_name")]
        verbose_name = "Embedding Model"
        verbose_name_plural = "Embedding Models"

    def __str__(self):
        return f"{self.name} ({self.model_name})"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        if self.is_default:
            qs = EmbeddingModelConfig.objects.filter(is_default=True)
            if self.tenant_id:
                qs = qs.filter(tenant=self.tenant)
            else:
                qs = qs.filter(tenant__isnull=True)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                raise ValidationError(
                    {
                        "is_default": "Only one default embedding model is allowed per scope."
                    }
                )


@register_setting
class AIProviderSettings(BaseSiteSetting):
    """Global AI selection settings shown under Wagtail Settings sidebar."""

    active_provider_type = models.CharField(
        max_length=32,
        choices=ProviderType.choices,
        default=ProviderType.OPENAI,
    )
    openai_api_key = models.CharField(max_length=255, blank=True)
    gemini_api_key = models.CharField(max_length=255, blank=True)
    groq_api_key = models.CharField(max_length=255, blank=True)
    ollama_base_url = models.URLField(blank=True, default="http://localhost:11434/v1")
    local_openai_base_url = models.URLField(blank=True, default="http://localhost:8001/v1")
    local_openai_api_key = models.CharField(max_length=255, blank=True)

    default_provider = models.ForeignKey(
        AIProviderConfig,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="default_provider_settings",
    )
    default_llm_model = models.ForeignKey(
        LLMModelConfig,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="default_llm_settings",
    )
    default_embedding_model = models.ForeignKey(
        EmbeddingModelConfig,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="default_embedding_settings",
    )
    allow_local_llm = models.BooleanField(default=True)
    allow_openai = models.BooleanField(default=True)
    allow_gemini = models.BooleanField(default=True)
    allow_groq = models.BooleanField(default=True)

    panels = [
        MultiFieldPanel(
            [
                FieldPanel("active_provider_type"),
                FieldPanel("default_provider"),
                FieldPanel("default_llm_model"),
                FieldPanel("default_embedding_model"),
            ],
            heading="Default AI Runtime",
        ),
        MultiFieldPanel(
            [
                FieldPanel("openai_api_key"),
                FieldPanel("gemini_api_key"),
                FieldPanel("groq_api_key"),
                FieldPanel("ollama_base_url"),
                FieldPanel("local_openai_base_url"),
                FieldPanel("local_openai_api_key"),
            ],
            heading="Provider Connection Forms",
        ),
        MultiFieldPanel(
            [
                FieldPanel("allow_local_llm"),
                FieldPanel("allow_openai"),
                FieldPanel("allow_gemini"),
                FieldPanel("allow_groq"),
            ],
            heading="Allowed Provider Types",
        ),
        MultiFieldPanel(
            [
                ReadOnlyPanel("proxy_status_display"),
                ReadOnlyPanel("runtime_inputs_display"),
                ReadOnlyPanel("provider_connection_status_display"),
            ],
            heading="Runtime Proxy and Connection Status",
        ),
    ]

    class Meta:
        verbose_name = "AI Provider Settings"

    @staticmethod
    def _first_env(*names):
        for name in names:
            value = os.getenv(name, "").strip()
            if value:
                return value
        return ""

    @staticmethod
    def _mask_secret(value):
        if not value:
            return "(missing)"
        if len(value) <= 4:
            return "*" * len(value)
        return f"{'*' * (len(value) - 4)}{value[-4:]}"

    @staticmethod
    def _normalize_local_base_url(value):
        if not value:
            return ""
        value = value.strip()
        if value.startswith("http://localhost"):
            value = value.replace("http://localhost", "http://127.0.0.1", 1)
        if value.startswith("https://localhost"):
            value = value.replace("https://localhost", "https://127.0.0.1", 1)
        if value.endswith("/"):
            value = value[:-1]
        if not value.endswith("/v1"):
            value = f"{value}/v1"
        return value

    @property
    def effective_ollama_base_url(self):
        return self._normalize_local_base_url(
            self.ollama_base_url
            or self._first_env("OLLAMA_BASE_URL", "OLLAMA_HOST")
            or "http://127.0.0.1:11434/v1"
        )

    @property
    def effective_local_openai_base_url(self):
        return self._normalize_local_base_url(
            self.local_openai_base_url
            or self._first_env("LOCAL_OPENAI_BASE_URL")
            or "http://127.0.0.1:8001/v1"
        )

    def _effective_proxy_map(self):
        return {
            "HTTP_PROXY": self._first_env("HTTP_PROXY", "http_proxy"),
            "HTTPS_PROXY": self._first_env("HTTPS_PROXY", "https_proxy"),
            "ALL_PROXY": self._first_env("ALL_PROXY", "all_proxy"),
            "NO_PROXY": self._first_env("NO_PROXY", "no_proxy"),
        }

    @property
    def proxy_status_display(self):
        proxies = self._effective_proxy_map()
        rows = []
        for key, value in proxies.items():
            shown = value or "(not set)"
            rows.append(
                f'<tr><td style="padding:6px 8px; font-weight:600;">{key}</td><td style="padding:6px 8px;">{shown}</td></tr>'
            )
        return format_html(
            '<div style="padding:10px; border:1px solid #dbe5f0; background:#fbfdff; border-radius:8px;">'
            '<strong style="display:block; margin-bottom:8px; color:#253858;">System proxy (auto-read at runtime)</strong>'
            '<table style="width:100%; border-collapse:collapse; font-size:12px;">{}</table>'
            '</div>',
            mark_safe("".join(rows)),
        )

    @property
    def runtime_inputs_display(self):
        openai_key = self.openai_api_key or self._first_env("OPENAI_API_KEY")
        gemini_key = self.gemini_api_key or self._first_env("GOOGLE_API_KEY", "GEMINI_API_KEY")
        groq_key = self.groq_api_key or self._first_env("GROQ_API_KEY")
        local_key = self.local_openai_api_key or self._first_env("LOCAL_OPENAI_API_KEY")

        return format_html(
            '<div style="padding:10px; border:1px solid #dbe5f0; background:#fbfdff; border-radius:8px;">'
            '<strong style="display:block; margin-bottom:8px; color:#253858;">Effective runtime inputs</strong>'
            '<ul style="margin:0; padding-left:18px; color:#30486f; font-size:12px;">'
            '<li>Active Provider Type: <strong>{}</strong></li>'
            '<li>Ollama Base URL: <strong>{}</strong></li>'
            '<li>Local OpenAI Base URL: <strong>{}</strong></li>'
            '<li>OpenAI Key: <strong>{}</strong></li>'
            '<li>Gemini Key: <strong>{}</strong></li>'
            '<li>Groq Key: <strong>{}</strong></li>'
            '<li>Local OpenAI Key: <strong>{}</strong></li>'
            '</ul>'
            '</div>',
            self.active_provider_type,
            self.effective_ollama_base_url,
            self.effective_local_openai_base_url,
            self._mask_secret(openai_key),
            self._mask_secret(gemini_key),
            self._mask_secret(groq_key),
            self._mask_secret(local_key),
        )

    def _connection_target(self):
        provider_type = self.active_provider_type
        if provider_type == ProviderType.OLLAMA:
            return {
                "url": f"{self.effective_ollama_base_url.rstrip('/')}/models",
                "headers": {},
                "label": "Ollama /models",
            }
        if provider_type == ProviderType.LOCAL_OPENAI:
            key = self.local_openai_api_key or self._first_env("LOCAL_OPENAI_API_KEY")
            headers = {"Authorization": f"Bearer {key}"} if key else {}
            return {
                "url": f"{self.effective_local_openai_base_url.rstrip('/')}/models",
                "headers": headers,
                "label": "Local OpenAI-Compatible /models",
            }
        if self.default_provider_id and self.default_provider.base_url:
            base = self.default_provider.base_url.rstrip("/")
            parsed = urlparse(base)
            if parsed.path.endswith("/v1"):
                base = base
            return {
                "url": f"{base}/models",
                "headers": {},
                "label": "Default Provider /models",
            }
        return {"url": "", "headers": {}, "label": "No target configured"}

    @property
    def provider_connection_status_display(self):
        target = self._connection_target()
        url = target["url"]
        if not url:
            return format_html(
                '<div style="padding:10px; background:#fff3cd; border:1px solid #ffe69c; border-radius:8px; color:#7a5d00;">'
                '<strong>Connection check unavailable:</strong> configure active provider base URL first.'
                '</div>'
            )

        try:
            response = httpx.get(
                url,
                headers=target["headers"],
                timeout=8,
                follow_redirects=True,
                trust_env=True,
            )
            if response.status_code < 400:
                return format_html(
                    '<div style="padding:10px; background:#d4edda; border:1px solid #c3e6cb; border-radius:8px; color:#155724;">'
                    '<strong>Connected</strong><br>'
                    '<small>Target: {}</small><br>'
                    '<small>URL: {}</small><br>'
                    '<small>HTTP Status: {}</small>'
                    '</div>',
                    target["label"],
                    url,
                    response.status_code,
                )
            return format_html(
                '<div style="padding:10px; background:#f8d7da; border:1px solid #f5c6cb; border-radius:8px; color:#721c24;">'
                '<strong>Connection failed</strong><br>'
                '<small>Target: {}</small><br>'
                '<small>URL: {}</small><br>'
                '<small>HTTP Status: {}</small><br>'
                '<small>Body: {}</small>'
                '</div>',
                target["label"],
                url,
                response.status_code,
                response.text[:180],
            )
        except Exception as exc:
            return format_html(
                '<div style="padding:10px; background:#f8d7da; border:1px solid #f5c6cb; border-radius:8px; color:#721c24;">'
                '<strong>Connection failed</strong><br>'
                '<small>Target: {}</small><br>'
                '<small>URL: {}</small><br>'
                '<small>Error: {}</small>'
                '</div>',
                target["label"],
                url,
                str(exc),
            )

    def save(self, *args, **kwargs):
        if not self.openai_api_key:
            self.openai_api_key = self._first_env("OPENAI_API_KEY")
        if not self.gemini_api_key:
            self.gemini_api_key = self._first_env("GOOGLE_API_KEY", "GEMINI_API_KEY")
        if not self.groq_api_key:
            self.groq_api_key = self._first_env("GROQ_API_KEY")
        if not self.local_openai_api_key:
            self.local_openai_api_key = self._first_env("LOCAL_OPENAI_API_KEY")

        self.ollama_base_url = self.effective_ollama_base_url
        self.local_openai_base_url = self.effective_local_openai_base_url

        super().save(*args, **kwargs)
