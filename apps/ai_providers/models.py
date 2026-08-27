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


class ReasoningProviderProfile(AbstractBaseModel):
    """Generic post-retrieval generation provider profile.

    This snippet is intentionally self-contained so admins can switch provider,
    model, endpoint URL and credentials from UI without code changes.
    """

    class ProviderType(models.TextChoices):
        OPENAI = "openai", "OpenAI"
        GEMINI = "gemini", "Google Gemini"
        OLLAMA = "ollama", "Ollama Local"
        OPENAI_COMPATIBLE = "openai_compatible", "OpenAI Compatible"

    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    provider_type = models.CharField(max_length=32, choices=ProviderType.choices)
    model_name = models.CharField(max_length=160)
    endpoint_url = models.URLField(blank=True)
    api_key = models.CharField(max_length=255, blank=True)
    api_key_env_var = models.CharField(
        max_length=120,
        blank=True,
        help_text="Optional environment variable containing API key.",
    )
    headers = models.JSONField(default=dict, blank=True)
    timeout_seconds = models.PositiveIntegerField(default=60)
    temperature = models.FloatField(default=0.2)
    max_tokens = models.PositiveIntegerField(default=1024)
    top_p = models.FloatField(default=1.0)
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(
        default=True,
        verbose_name="Active (runtime enabled)",
        help_text="Turn off to fully disable this reasoning profile.",
    )
    show_on_dashboard = models.BooleanField(
        default=True,
        verbose_name="Visible in dashboard",
        help_text="If disabled, this profile is hidden from Qdrant dashboard reasoning provider list.",
    )
    sort_order = models.PositiveIntegerField(default=0)

    panels = [
        MultiFieldPanel(
            [
                FieldPanel("name"),
                FieldPanel("slug"),
                FieldPanel("provider_type"),
                FieldPanel("is_active"),
                FieldPanel("show_on_dashboard"),
                FieldPanel("is_default"),
                FieldPanel("sort_order"),
            ],
            heading="Identity",
        ),
        MultiFieldPanel(
            [
                FieldPanel("model_name"),
                FieldPanel("temperature"),
                FieldPanel("max_tokens"),
                FieldPanel("top_p"),
            ],
            heading="Generation Runtime",
        ),
        MultiFieldPanel(
            [
                FieldPanel("endpoint_url"),
                FieldPanel("api_key"),
                FieldPanel("api_key_env_var"),
                FieldPanel("headers"),
                FieldPanel("timeout_seconds"),
                ReadOnlyPanel("connection_status_display"),
            ],
            heading="Connection",
        ),
    ]

    class Meta:
        ordering = ["sort_order", "name"]
        verbose_name = "Reasoning Provider Profile"
        verbose_name_plural = "Reasoning Provider Profiles"

    def __str__(self):
        return self.name

    @property
    def enabled_status(self):
        return "Visible" if self.show_on_dashboard else "Hidden"

    @property
    def active_status(self):
        return "Active" if self.is_active else "Inactive"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        if self.is_default:
            ReasoningProviderProfile.objects.filter(is_default=True).exclude(pk=self.pk).update(
                is_default=False
            )
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        if self.provider_type in {self.ProviderType.OPENAI, self.ProviderType.GEMINI}:
            if not self.api_key and not self.api_key_env_var:
                raise ValidationError(
                    {"api_key_env_var": "Provide api_key or api_key_env_var for this provider."}
                )

    def get_api_key(self):
        if self.api_key:
            return self.api_key
        if not self.api_key_env_var:
            return ""
        return os.getenv(self.api_key_env_var, "")

    @staticmethod
    def _normalize_local(url):
        if not url:
            return ""
        result = url.strip()
        result = result.replace("http://localhost", "http://127.0.0.1")
        result = result.replace("https://localhost", "https://127.0.0.1")
        return result.rstrip("/")

    def effective_endpoint_url(self):
        if self.endpoint_url:
            return self._normalize_local(self.endpoint_url)
        if self.provider_type == self.ProviderType.OPENAI:
            return "https://api.openai.com/v1"
        if self.provider_type == self.ProviderType.GEMINI:
            return "https://generativelanguage.googleapis.com/v1beta"
        if self.provider_type == self.ProviderType.OLLAMA:
            return "http://127.0.0.1:11434/v1"
        if self.provider_type == self.ProviderType.OPENAI_COMPATIBLE:
            return "http://127.0.0.1:8001/v1"
        return ""

    def _models_url(self, endpoint_url=None):
        endpoint = self._normalize_local(endpoint_url) if endpoint_url else self.effective_endpoint_url()
        if self.provider_type == self.ProviderType.GEMINI:
            return f"{endpoint}/models"
        if endpoint.endswith("/models"):
            return endpoint
        return f"{endpoint}/models"

    def test_connection(
        self,
        endpoint_url=None,
        api_key=None,
        timeout_seconds=None,
        headers=None,
    ):
        import time

        log = []

        def trace(line):
            log.append(f"[{time.strftime('%H:%M:%S')}] {line}")

        url = self._models_url(endpoint_url=endpoint_url)
        if not url:
            trace("No endpoint configured.")
            return {"available": False, "detail": "No endpoint configured.", "status_code": 0, "latency_ms": 0, "log": log}

        headers_map = {"Content-Type": "application/json", **(self.headers or {})}
        if headers:
            headers_map.update(headers)
        api_key = (api_key or "").strip() or self.get_api_key()
        params = None
        if self.provider_type == self.ProviderType.GEMINI and api_key:
            params = {"key": api_key}
        elif api_key:
            headers_map["Authorization"] = f"Bearer {api_key}"
        elif self.provider_type == self.ProviderType.OLLAMA:
            headers_map["Authorization"] = "Bearer ollama"

        hostname = (urlparse(url).hostname or "").lower()
        trust_env = hostname not in {"localhost", "127.0.0.1", "0.0.0.0"}
        timeout = int(timeout_seconds or self.timeout_seconds or 60)

        trace(f"Provider: {self.name} ({self.get_provider_type_display()})")
        trace(f"GET {url}")
        trace(f"Timeout: {timeout}s")
        trace(f"trust_env: {trust_env}")
        trace(
            "Authorization header: "
            + ("Bearer ****" + api_key[-4:] if api_key else "not sent")
        )

        try:
            started = time.perf_counter()
            with httpx.Client(timeout=timeout, trust_env=trust_env) as client:
                response = client.get(url, headers=headers_map, params=params)
            latency_ms = int((time.perf_counter() - started) * 1000)
            trace(f"Status: {response.status_code} {response.reason_phrase}")
            snippet = (response.text or "")[:300]
            if snippet:
                trace(f"Body: {snippet}")
            if response.status_code < 500:
                trace("Result: reachable")
                return {
                    "available": True,
                    "detail": f"Reachable (HTTP {response.status_code}).",
                    "status_code": response.status_code,
                    "latency_ms": latency_ms,
                    "log": log,
                }
            trace("Result: unavailable (server error)")
            return {
                "available": False,
                "detail": f"Endpoint returned HTTP {response.status_code}.",
                "status_code": response.status_code,
                "latency_ms": latency_ms,
                "log": log,
            }
        except Exception as exc:
            trace(f"Request failed: {type(exc).__name__}: {exc}")
            return {"available": False, "detail": str(exc), "status_code": 0, "latency_ms": 0, "log": log}

    def to_card_dict(self):
        return {
            "slug": self.slug,
            "name": self.name,
            "provider_type": self.provider_type,
            "model_name": self.model_name,
            "endpoint_url": self.effective_endpoint_url(),
            "api_key_set": bool(self.get_api_key()),
            "timeout_seconds": self.timeout_seconds,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "top_p": self.top_p,
            "is_default": self.is_default,
            "is_active": self.is_active,
            "show_on_dashboard": self.show_on_dashboard,
        }

    @property
    def connection_status_display(self):
        result = self.test_connection()
        color = "#155724" if result.get("available") else "#721c24"
        bg = "#d4edda" if result.get("available") else "#f8d7da"
        border = "#c3e6cb" if result.get("available") else "#f5c6cb"
        return format_html(
            '<div style="padding:10px; border:1px solid {}; background:{}; border-radius:8px; color:{};">'
            '<strong>{}</strong><br>'
            '<small>Endpoint: {}</small><br>'
            '<small>Model: {}</small><br>'
            '<small>Detail: {}</small>'
            '</div>',
            border,
            bg,
            color,
            "Connected" if result.get("available") else "Unavailable",
            self.effective_endpoint_url() or "(not configured)",
            self.model_name or "(not configured)",
            result.get("detail") or "",
        )


@register_setting
class AIProviderSettings(BaseSiteSetting):
    """Global AI selection settings shown under Wagtail Settings sidebar."""

    RUNTIME_PROVIDER_CHOICES = [
        (ProviderType.OPENAI, "OpenAI"),
        (ProviderType.GEMINI, "Google Gemini"),
        (ProviderType.OLLAMA, "Ollama Local"),
        (ProviderType.LOCAL_OPENAI, "OpenAI Compatible"),
    ]

    active_provider_type = models.CharField(
        max_length=32,
        choices=RUNTIME_PROVIDER_CHOICES,
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
        limit_choices_to={"is_active": True},
    )
    default_llm_model = models.ForeignKey(
        LLMModelConfig,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="default_llm_settings",
        limit_choices_to={"is_active": True},
    )
    default_embedding_model = models.ForeignKey(
        EmbeddingModelConfig,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="default_embedding_settings",
        limit_choices_to={"is_active": True},
    )
    default_reasoning_profile = models.ForeignKey(
        ReasoningProviderProfile,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="default_reasoning_settings",
        limit_choices_to={"is_active": True, "show_on_dashboard": True},
    )
    enable_embedding_profiles = models.BooleanField(
        default=True,
        help_text="If disabled, embedding profile selection/configuration is hidden from upload/dashboard UI.",
    )
    enable_reasoning_profiles = models.BooleanField(
        default=True,
        help_text="If disabled, reasoning profile selection is hidden and runtime falls back to legacy LLM model settings.",
    )
    allow_local_llm = models.BooleanField(default=True)
    allow_openai = models.BooleanField(default=True)
    allow_gemini = models.BooleanField(default=True)
    allow_groq = models.BooleanField(default=True)

    panels = [
        ReadOnlyPanel("provider_console_display", heading=""),
    ]

    class Meta:
        verbose_name = "AI Provider Settings"

    @property
    def provider_console_display(self):
        profiles = list(
            ReasoningProviderProfile.objects.filter(is_active=True, show_on_dashboard=True).order_by(
                "sort_order", "name"
            )
        )

        def score_for_provider(provider_type):
            if provider_type in {ReasoningProviderProfile.ProviderType.OPENAI, ReasoningProviderProfile.ProviderType.GEMINI}:
                return 5
            if provider_type == ReasoningProviderProfile.ProviderType.OLLAMA:
                return 4
            return 4

        def stars(score):
            return "★" * max(0, score) + "☆" * max(0, 5 - score)

        def badge_labels(provider_type):
            if provider_type == ReasoningProviderProfile.ProviderType.OLLAMA:
                return ["Cost Effective", "Fully Offline"]
            if provider_type == ReasoningProviderProfile.ProviderType.OPENAI:
                return ["Highest Accuracy"]
            if provider_type == ReasoningProviderProfile.ProviderType.GEMINI:
                return ["Balanced", "Fast"]
            return ["Flexible"]

        def capability(provider_type):
            if provider_type == ReasoningProviderProfile.ProviderType.OLLAMA:
                return "Offline (Local)"
            if provider_type in {ReasoningProviderProfile.ProviderType.OPENAI, ReasoningProviderProfile.ProviderType.GEMINI}:
                return "Online (Cloud)"
            return "Hybrid"

        runtime_map = {
            ReasoningProviderProfile.ProviderType.OPENAI: ProviderType.OPENAI,
            ReasoningProviderProfile.ProviderType.GEMINI: ProviderType.GEMINI,
            ReasoningProviderProfile.ProviderType.OLLAMA: ProviderType.OLLAMA,
            ReasoningProviderProfile.ProviderType.OPENAI_COMPATIBLE: ProviderType.LOCAL_OPENAI,
        }
        active_slug = ""
        if self.default_reasoning_profile_id:
            active_slug = self.default_reasoning_profile.slug
        else:
            matched = next(
                (
                    p
                    for p in profiles
                    if runtime_map.get(p.provider_type) == self.active_provider_type
                ),
                None,
            )
            active_slug = matched.slug if matched else ""

        cards_html = []
        for p in profiles:
            is_active = p.slug == active_slug
            dot = "#22c55e" if p.provider_type == ReasoningProviderProfile.ProviderType.OLLAMA else "#ef4444"
            if p.provider_type == ReasoningProviderProfile.ProviderType.GEMINI:
                dot = "#f59e0b"
            if p.provider_type == ReasoningProviderProfile.ProviderType.OPENAI_COMPATIBLE:
                dot = "#3b82f6"

            badges = "".join(
                [f'<span class="aips-pill">{label}</span>' for label in badge_labels(p.provider_type)]
            )
            edit_url = f"/admin/snippets/ai_providers/reasoningproviderprofile/edit/{p.pk}/"
            if is_active:
                use_action = mark_safe('<button type="button" class="aips-btn primary" disabled>Active profile</button>')
            else:
                use_action = format_html(
                    '<button type="button" class="aips-btn primary aips-use-btn" data-profile-slug="{}">Use this profile</button>',
                    p.slug,
                )
            cards_html.append(
                format_html(
                    '<div class="aips-card {}">'
                    '<div class="aips-topline">'
                    '<div class="aips-title"><span class="aips-dot" style="background:{}"></span>{}</div>'
                    '{}'
                    '</div>'
                    '<div class="aips-model">{}</div>'
                    '<div class="aips-pill-row">{}</div>'
                    '<div class="aips-kv-grid">'
                    '<div class="aips-kv"><div class="k">Provider</div><div class="v">{}</div></div>'
                    '<div class="aips-kv"><div class="k">Performance</div><div class="v">{}</div></div>'
                    '<div class="aips-kv"><div class="k">Timeout</div><div class="v">{}s</div></div>'
                    '<div class="aips-kv"><div class="k">Capability</div><div class="v">{}</div></div>'
                    '</div>'
                    '<div class="aips-meta">Endpoint: {}</div>'
                    '<div class="aips-actions">'
                    '{}'
                    '<a class="aips-btn secondary" href="{}">Configure</a>'
                    '</div>'
                    '</div>',
                    "active" if is_active else "",
                    dot,
                    p.name,
                    mark_safe('<span class="aips-badge green">Active</span>') if is_active else "",
                    p.model_name or "-",
                    mark_safe(badges),
                    p.get_provider_type_display(),
                    stars(score_for_provider(p.provider_type)),
                    p.timeout_seconds or 60,
                    capability(p.provider_type),
                    p.effective_endpoint_url() or "-",
                    use_action,
                    edit_url,
                )
            )

        body_html = mark_safe("".join(cards_html)) if cards_html else mark_safe(
            '<div class="aips-card"><div class="aips-meta">No visible reasoning profiles found in snippets.</div></div>'
        )

        shell_html = format_html(
            '<style>'
            '.aips-shell {{ border:1px solid #dce6f5; border-radius:14px; background:#fbfdff; overflow:hidden; }}'
            '.aips-head {{ padding:14px 16px; background:linear-gradient(150deg,#f6faff 0%, #e9f2ff 100%); border-bottom:1px solid #d8e5fb; }}'
            '.aips-head h3 {{ margin:0; font-size:15px; color:#173660; }}'
            '.aips-head .aips-sub {{ font-size:12px; color:#4d678a; margin-top:4px; }}'
            '.aips-runtime {{ margin-top:10px; display:flex; align-items:center; gap:8px; flex-wrap:wrap; }}'
            '.aips-runtime-badge {{ border-radius:999px; padding:4px 9px; font-size:11px; font-weight:700; border:1px solid #d7e3f8; background:#eef4ff; color:#244874; }}'
            '.aips-runtime-badge.ok {{ border-color:#b8e4ce; background:#e9f9f1; color:#13613d; }}'
            '.aips-runtime-badge.err {{ border-color:#f2c0c0; background:#fdeeee; color:#7d1d1d; }}'
            '.aips-runtime-btn {{ border:1px solid #c9d8f5; background:#fff; color:#29456f; border-radius:8px; padding:5px 9px; font-size:11px; font-weight:700; cursor:pointer; }}'
            '.aips-body {{ padding:14px; background:#f9fbff; }}'
            '.aips-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(280px,1fr)); gap:14px; }}'
            '.aips-card {{ border:1px solid #d6e4fb; background:#fff; border-radius:14px; padding:14px; box-shadow:0 2px 8px rgba(16,24,40,.04); }}'
            '.aips-card.active {{ border-color:#9dddb9; background:#f4fbf7; }}'
            '.aips-topline {{ display:flex; align-items:flex-start; justify-content:space-between; gap:8px; margin-bottom:2px; }}'
            '.aips-title {{ margin:0; font-size:14px; font-weight:800; color:#142f56; display:flex; align-items:center; gap:8px; }}'
            '.aips-dot {{ width:10px; height:10px; border-radius:999px; flex:none; margin-top:4px; }}'
            '.aips-model {{ font-size:12px; color:#6a7f9f; margin-bottom:10px; }}'
            '.aips-pill-row {{ display:flex; flex-wrap:wrap; gap:6px; margin-bottom:10px; }}'
            '.aips-pill {{ border-radius:999px; padding:3px 8px; font-size:10px; font-weight:700; border:1px solid #cfe0fb; background:#eef4ff; color:#2f5fae; }}'
            '.aips-kv-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:8px; margin-bottom:8px; }}'
            '.aips-kv .k {{ font-size:10px; color:#6e83a0; letter-spacing:.03em; text-transform:uppercase; }}'
            '.aips-kv .v {{ font-size:12px; color:#1f3f67; margin-top:2px; font-weight:600; }}'
            '.aips-meta {{ font-size:12px; color:#4e6485; margin-bottom:4px; }}'
            '.aips-actions {{ display:flex; gap:8px; margin-top:10px; }}'
            '.aips-badge {{ border-radius:999px; padding:3px 8px; font-size:10px; font-weight:700; border:1px solid #b8e4ce; background:#e9f9f1; color:#13613d; }}'
            '.aips-btn {{ display:inline-block; text-decoration:none; border:1px solid #c9d8f5; background:#fff; color:#29456f; border-radius:8px; padding:7px 11px; font-size:12px; font-weight:700; }}'
            '.aips-btn.primary {{ background:#2f6fed; border-color:#2f6fed; color:#fff; }}'
            '.aips-btn[disabled] {{ cursor:not-allowed; opacity:.75; }}'
            '.aips-btn.secondary {{ background:#fff; border-color:#c6d6f6; color:#244874; }}'
            '.aips-toast {{ position:fixed; right:20px; bottom:20px; max-width:320px; padding:10px 12px; border-radius:10px; border:1px solid #cfe0fb; background:#eef4ff; color:#184072; font-size:12px; font-weight:600; box-shadow:0 6px 16px rgba(16,24,40,.14); opacity:0; pointer-events:none; transform:translateY(6px); transition:opacity .2s ease, transform .2s ease; z-index:3000; }}'
            '.aips-toast.show {{ opacity:1; transform:translateY(0); }}'
            '.aips-toast.success {{ border-color:#b8e4ce; background:#e9f9f1; color:#13613d; }}'
            '.aips-toast.error {{ border-color:#f2c0c0; background:#fdeeee; color:#7d1d1d; }}'
            '</style>'
            '<div class="aips-shell">'
            '<div class="aips-head">'
            '<h3>AI Provider Control Center</h3>'
            '<div class="aips-sub">Showing only enabled reasoning profiles visible in snippets.</div>'
            '<div class="aips-runtime">'
            '<span id="aips-qdrant-badge" class="aips-runtime-badge">Qdrant: checking...</span>'
            '<span id="aips-ollama-badge" class="aips-runtime-badge">Ollama: checking...</span>'
            '<button type="button" id="aips-runtime-refresh" class="aips-runtime-btn">Refresh Runtime</button>'
            '</div>'
            '</div>'
            '<div class="aips-body">'
            '<div class="aips-grid">{}</div>'
            '<div id="aips-status" class="aips-meta" style="margin-top:12px;">Choose a profile to make it active for runtime chat reasoning.</div>'
            '</div>'
            '</div>'
            '<div id="aips-toast" class="aips-toast" aria-live="polite"></div>',
            body_html,
        )

        script_html = '''
<script>
(function(){
if (window.__aipsUseProfileInit) return;
window.__aipsUseProfileInit = true;

function showToast(message, tone){
const toast = document.getElementById('aips-toast');
if (!toast) return;
toast.textContent = message;
toast.classList.remove('success', 'error');
if (tone) toast.classList.add(tone);
toast.classList.add('show');
window.setTimeout(function(){
    toast.classList.remove('show');
}, 2200);
}

function hideFooterSaveButton(){
function applyHide(){
    const footer = document.querySelector('nav[aria-label="Actions (footer)"], nav.actions--primary.footer__container, nav.footer__container');
    if (!footer) return false;
    footer.style.display = 'none';
    return true;
}

if (!applyHide()) {
    window.setTimeout(applyHide, 150);
    window.setTimeout(applyHide, 600);
    let attempts = 0;
    const timer = window.setInterval(function(){
        attempts += 1;
        if (applyHide() || attempts >= 20) {
            window.clearInterval(timer);
        }
    }, 250);
}
}

function csrf(){
const c = document.cookie.split('; ').find((x) => x.indexOf('csrftoken=') === 0);
return c ? decodeURIComponent(c.split('=')[1]) : '';
}
hideFooterSaveButton();

async function refreshRuntimeHealth(){
const qBadge = document.getElementById('aips-qdrant-badge');
const oBadge = document.getElementById('aips-ollama-badge');
try {
    const res = await fetch('/api/v1/runtime-health/', {headers: {'Accept': 'application/json'}});
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error('Runtime health unavailable (' + res.status + ')');

    const q = data.qdrant || {};
    if (qBadge) {
        const ok = q.status === 'connected';
        qBadge.classList.remove('ok', 'err');
        qBadge.classList.add(ok ? 'ok' : 'err');
        qBadge.textContent = 'Qdrant: ' + (ok ? 'connected' : 'unavailable') + (q.latency_ms ? ' (' + q.latency_ms + 'ms)' : '');
    }

    const o = data.ollama || {};
    if (oBadge) {
        const ok = o.status === 'connected';
        oBadge.classList.remove('ok', 'err');
        oBadge.classList.add(ok ? 'ok' : 'err');
        const modelCount = Array.isArray(o.models) ? o.models.length : 0;
        oBadge.textContent = 'Ollama: ' + (ok ? 'connected' : 'unavailable') + (ok ? ' (' + modelCount + ' models)' : '');
    }
} catch (err) {
    if (qBadge) {
        qBadge.classList.remove('ok');
        qBadge.classList.add('err');
        qBadge.textContent = 'Qdrant: unavailable';
    }
    if (oBadge) {
        oBadge.classList.remove('ok');
        oBadge.classList.add('err');
        oBadge.textContent = 'Ollama: unavailable';
    }
}
}

const refreshBtn = document.getElementById('aips-runtime-refresh');
if (refreshBtn) {
    refreshBtn.addEventListener('click', function(){
        refreshRuntimeHealth();
    });
}
refreshRuntimeHealth();
window.setInterval(refreshRuntimeHealth, 30000);

document.addEventListener('click', async function(event){
const btn = event.target && event.target.closest ? event.target.closest('.aips-use-btn') : null;
if (!btn) return;
event.preventDefault();
const slug = btn.getAttribute('data-profile-slug') || '';
if (!slug) return;
const status = document.getElementById('aips-status');
const original = btn.textContent;
btn.disabled = true;
btn.textContent = 'Applying...';
if (status) status.textContent = 'Applying reasoning profile ' + slug + '...';
try {
    const res = await fetch('/api/v1/reasoning-profiles/' + slug + '/connection/', {
        method: 'POST',
        headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrf()},
        body: JSON.stringify({set_default: true}),
    });
    const payload = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(payload.error || payload.detail || ('Request failed: ' + res.status));
    if (status) status.textContent = 'Active reasoning profile updated. Reloading...';
    showToast('Reasoning profile updated successfully.', 'success');
    window.setTimeout(function(){
        window.location.reload();
    }, 500);
} catch (err) {
    if (status) status.textContent = 'Unable to update profile: ' + err.message;
    showToast('Unable to update profile: ' + err.message, 'error');
    btn.disabled = false;
    btn.textContent = original;
}
});
})();
</script>
'''
        return mark_safe(f"{shell_html}{script_html}")

    @property
    def settings_overview_display(self):
        active_reasoning = self.get_active_reasoning_profile()
        reasoning_name = active_reasoning.name if active_reasoning else "Not selected"
        provider_name = self.default_provider.name if self.default_provider_id else "Not selected"
        llm_name = self.default_llm_model.name if self.default_llm_model_id else "Not selected"
        embedding_name = self.default_embedding_model.name if self.default_embedding_model_id else "Not selected"
        return format_html(
            '<div style="padding:14px; border:1px solid #d7e2ff; border-radius:12px; '
            'background:linear-gradient(135deg, #f7f9ff 0%, #eef6ff 100%);">'
            '<div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:10px;">'
            '<strong style="font-size:14px; color:#1f3b73;">AI Runtime Snapshot</strong>'
            '<span style="font-size:12px; color:#3d5a80;">Provider: {}</span>'
            '</div>'
            '<div style="display:grid; grid-template-columns:repeat(2, minmax(220px, 1fr)); gap:10px;">'
            '<div style="padding:10px; background:#fff; border:1px solid #dfe7fb; border-radius:10px;">'
            '<div style="font-size:11px; color:#60769a; text-transform:uppercase; letter-spacing:.02em;">Reasoning Profiles</div>'
            '<div style="font-weight:600; color:#1d3557; margin-top:4px;">{}</div>'
            '<div style="font-size:12px; color:#4a6284; margin-top:4px;">Visibility: {}</div>'
            '</div>'
            '<div style="padding:10px; background:#fff; border:1px solid #dfe7fb; border-radius:10px;">'
            '<div style="font-size:11px; color:#60769a; text-transform:uppercase; letter-spacing:.02em;">Embedding Profiles</div>'
            '<div style="font-weight:600; color:#1d3557; margin-top:4px;">{}</div>'
            '<div style="font-size:12px; color:#4a6284; margin-top:4px;">Visibility: {}</div>'
            '</div>'
            '<div style="padding:10px; background:#fff; border:1px solid #dfe7fb; border-radius:10px;">'
            '<div style="font-size:11px; color:#60769a; text-transform:uppercase; letter-spacing:.02em;">Default AI Provider</div>'
            '<div style="font-weight:600; color:#1d3557; margin-top:4px;">{}</div>'
            '</div>'
            '<div style="padding:10px; background:#fff; border:1px solid #dfe7fb; border-radius:10px;">'
            '<div style="font-size:11px; color:#60769a; text-transform:uppercase; letter-spacing:.02em;">Default LLM Model</div>'
            '<div style="font-weight:600; color:#1d3557; margin-top:4px;">{}</div>'
            '</div>'
            '</div>'
            '</div>',
            self.get_active_provider_type_display(),
            reasoning_name,
            "Enabled" if self.enable_reasoning_profiles else "Disabled",
            embedding_name,
            "Enabled" if self.enable_embedding_profiles else "Disabled",
            provider_name,
            llm_name,
        )

    @property
    def reasoning_profiles_display(self):
        if not self.enable_reasoning_profiles:
            return format_html(
                '<div style="padding:10px; border:1px solid #ffe69c; background:#fff8e6; border-radius:10px; color:#7a5d00;">'
                '<strong>Reasoning profiles are disabled</strong><br>'
                '<small>Enable "Reasoning profiles" in settings to use snippet-based runtime controller selection.</small>'
                '</div>'
            )

        profiles = list(
            ReasoningProviderProfile.objects.filter(is_active=True, show_on_dashboard=True).order_by("sort_order", "name")
        )
        selected = self.get_active_reasoning_profile()
        if not profiles:
            return format_html(
                '<div style="padding:10px; border:1px solid #dbe5f0; background:#fbfdff; border-radius:10px; color:#355176;">'
                '<strong>No visible reasoning profiles</strong><br>'
                '<small>Create profiles in snippets and mark them as "Visible in dashboard".</small>'
                '</div>'
            )

        cards = []
        for profile in profiles:
            selected_badge = "<span style='font-size:11px; color:#0f5132; background:#d1f2e0; border:1px solid #b6e4cd; padding:2px 8px; border-radius:999px;'>Active</span>" if selected and selected.pk == profile.pk else ""
            cards.append(
                format_html(
                    '<div style="padding:10px; border:1px solid {}; border-radius:10px; background:{};">'
                    '<div style="display:flex; justify-content:space-between; gap:8px; align-items:center;">'
                    '<strong style="font-size:13px; color:#17325b;">{}</strong>{}'
                    '</div>'
                    '<div style="font-size:11px; color:#4f6688; margin-top:4px;">{} | model: {}</div>'
                    '<div style="font-size:11px; color:#5f7597; margin-top:4px;">{}</div>'
                    '</div>',
                    "#b6e4cd" if selected and selected.pk == profile.pk else "#dfe7fb",
                    "#f1fbf6" if selected and selected.pk == profile.pk else "#ffffff",
                    profile.name,
                    mark_safe(selected_badge),
                    profile.get_provider_type_display(),
                    profile.model_name,
                    profile.effective_endpoint_url() or "No endpoint configured",
                )
            )

        return format_html(
            '<div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(220px, 1fr)); gap:10px;">{}</div>',
            mark_safe("".join(cards)),
        )

    def get_active_reasoning_profile(self):
        if not self.enable_reasoning_profiles:
            return None
        if (
            self.default_reasoning_profile_id
            and self.default_reasoning_profile.is_active
            and self.default_reasoning_profile.show_on_dashboard
        ):
            return self.default_reasoning_profile
        return ReasoningProviderProfile.objects.filter(
            is_active=True,
            is_default=True,
            show_on_dashboard=True,
        ).first()

    @staticmethod
    def _reasoning_to_runtime_type(provider_type):
        mapping = {
            ReasoningProviderProfile.ProviderType.OPENAI: ProviderType.OPENAI,
            ReasoningProviderProfile.ProviderType.GEMINI: ProviderType.GEMINI,
            ReasoningProviderProfile.ProviderType.OLLAMA: ProviderType.OLLAMA,
            ReasoningProviderProfile.ProviderType.OPENAI_COMPATIBLE: ProviderType.LOCAL_OPENAI,
        }
        return mapping.get(provider_type, ProviderType.OLLAMA)

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
            return mark_safe(
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

        if not self.enable_reasoning_profiles:
            self.default_reasoning_profile = None
        if not self.enable_embedding_profiles:
            self.default_embedding_model = None

        active_reasoning = self.get_active_reasoning_profile()
        if active_reasoning:
            self.active_provider_type = self._reasoning_to_runtime_type(active_reasoning.provider_type)

        super().save(*args, **kwargs)
