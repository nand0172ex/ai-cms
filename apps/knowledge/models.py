"""Knowledge base and Qdrant connection models."""

import os

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.html import escape, format_html
from django.utils.safestring import mark_safe
from django.utils.text import slugify
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.contrib.settings.models import BaseSiteSetting, register_setting
from wagtail.snippets.models import register_snippet

from apps.core.models import AbstractBaseModel
from apps.knowledge.panels import ReadOnlyPanel


class QdrantConnection(AbstractBaseModel):
    """Connection profile for a Qdrant cluster."""

    tenant = models.ForeignKey(
        "tenants.Tenant",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="qdrant_connections",
        help_text="Optional tenant scope. Leave empty for global connection.",
    )
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140)

    url = models.URLField(default="http://localhost:6333")
    api_key_env_var = models.CharField(
        max_length=120,
        blank=True,
        help_text="Environment variable containing Qdrant API key.",
    )
    api_key = models.CharField(
        max_length=255,
        blank=True,
        help_text="Optional direct API key for zero-touch admin setup.",
    )
    prefer_grpc = models.BooleanField(default=False)
    verify_tls = models.BooleanField(default=True)
    timeout_seconds = models.PositiveIntegerField(default=30)

    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]
        unique_together = [("tenant", "slug")]
        verbose_name = "Qdrant Connection"
        verbose_name_plural = "Qdrant Connections"

    def __str__(self):
        scope = self.tenant.slug if self.tenant_id else "global"
        return f"{self.name} ({scope})"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        if self.is_default:
            qs = QdrantConnection.objects.filter(is_default=True)
            if self.tenant_id:
                qs = qs.filter(tenant=self.tenant)
            else:
                qs = qs.filter(tenant__isnull=True)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                raise ValidationError(
                    {"is_default": "Only one default connection is allowed per scope."}
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


class KnowledgeBase(AbstractBaseModel):
    """
    A collection of documents/content for RAG retrieval.
    Each knowledge base corresponds to a Qdrant collection.
    """
    tenant = models.ForeignKey(
        "tenants.Tenant",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="knowledge_bases",
        help_text="Optional tenant scope. Leave empty for global knowledge base.",
    )
    qdrant_connection = models.ForeignKey(
        QdrantConnection,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="knowledge_bases",
        help_text="Optional explicit connection. Uses default connection when empty.",
    )

    name = models.CharField(
        max_length=255,
        help_text="Display name for knowledge base"
    )
    slug = models.SlugField(
        help_text="URL-friendly identifier"
    )
    description = models.TextField(
        blank=True,
        help_text="Description of knowledge base content"
    )

    # Qdrant Configuration
    collection_name = models.CharField(
        max_length=255,
        help_text="Qdrant collection name"
    )
    vector_size = models.IntegerField(
        default=1536,
        help_text="Embedding vector dimension (default 1536 for OpenAI)"
    )

    # Retrieval Configuration
    top_k = models.IntegerField(
        default=5,
        help_text="Number of documents to retrieve per query"
    )
    similarity_threshold = models.FloatField(
        default=0.7,
        help_text="Minimum similarity score (0.0 - 1.0)"
    )

    # Status
    is_active = models.BooleanField(
        default=True,
        help_text="Enable/disable this knowledge base"
    )
    document_count = models.IntegerField(
        default=0,
        help_text="Number of documents in this knowledge base"
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Knowledge Base"
        verbose_name_plural = "Knowledge Bases"
        unique_together = [("tenant", "slug"), ("tenant", "collection_name")]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        if not self.collection_name:
            self.collection_name = slugify(self.name).replace('-', '_')
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        if self.top_k <= 0:
            raise ValidationError({"top_k": "top_k must be greater than 0."})
        if self.vector_size <= 0:
            raise ValidationError({"vector_size": "vector_size must be greater than 0."})
        if not 0 <= self.similarity_threshold <= 1:
            raise ValidationError(
                {"similarity_threshold": "similarity_threshold must be between 0 and 1."}
            )

    @property
    def effective_collection_name(self):
        if self.tenant_id:
            return f"{self.tenant.slug}__{self.collection_name}"
        return self.collection_name


@register_snippet
class EmbeddingProfile(AbstractBaseModel):
    """Describes an embedding provider option offered during upload.

    Selecting a profile only records the user's intent as metadata on the
    uploaded document; it does not change how chunks are vectorized today.
    New providers can be added here by staff without any code changes.
    """

    class ProviderType(models.TextChoices):
        DEFAULT = "default", "Default"
        HUGGINGFACE = "huggingface", "HuggingFace"
        OPENAI = "openai", "OpenAI"
        AZURE_OPENAI = "azure_openai", "Azure OpenAI"
        OLLAMA = "ollama", "Ollama"
        LOCAL = "local", "Local Models"
        CUSTOM = "custom", "Custom API"

    class CostIndicator(models.TextChoices):
        FREE = "free", "Free"
        LOW = "low", "Low Cost"
        MEDIUM = "medium", "Medium Cost"
        HIGH = "high", "High Cost"

    class Capability(models.TextChoices):
        ONLINE = "online", "Online (Cloud)"
        OFFLINE = "offline", "Offline (Local)"
        HYBRID = "hybrid", "Hybrid"

    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    provider_type = models.CharField(
        max_length=32, choices=ProviderType.choices, default=ProviderType.DEFAULT
    )
    model_name = models.CharField(
        max_length=160, blank=True, help_text="Embedding model identifier, e.g. text-embedding-3-small"
    )
    embedding_dimensions = models.PositiveIntegerField(default=1536)
    best_use_case = models.CharField(
        max_length=255, blank=True, help_text="One line describing when to pick this provider"
    )
    performance_rating = models.PositiveSmallIntegerField(
        default=3, help_text="Performance rating from 1 (basic) to 5 (excellent)"
    )
    cost_indicator = models.CharField(
        max_length=20, choices=CostIndicator.choices, default=CostIndicator.FREE
    )
    capability = models.CharField(
        max_length=20, choices=Capability.choices, default=Capability.ONLINE
    )
    highlights = models.JSONField(
        default=list,
        blank=True,
        help_text="Short bullet highlights shown on the provider card, e.g. [\"Good general purpose embeddings\"]",
    )
    why_choose = models.TextField(
        blank=True, help_text="Shown in the 'Why choose this provider?' help section"
    )
    badge_recommended = models.BooleanField(default=False, verbose_name="Badge: Recommended")
    badge_cost_effective = models.BooleanField(default=False, verbose_name="Badge: Cost Effective")
    badge_fully_offline = models.BooleanField(default=False, verbose_name="Badge: Fully Offline")
    badge_fastest = models.BooleanField(default=False, verbose_name="Badge: Fastest")
    badge_highest_accuracy = models.BooleanField(default=False, verbose_name="Badge: Highest Accuracy")
    is_default = models.BooleanField(
        default=False, help_text="Used automatically when the uploader does not pick a profile"
    )
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    base_url = models.URLField(
        blank=True, help_text="Provider API endpoint used for the availability check, e.g. https://api.openai.com/v1"
    )
    api_key = models.CharField(max_length=255, blank=True, help_text="Optional API key for this provider")
    api_key_env_var = models.CharField(
        max_length=120, blank=True, help_text="Optional environment variable name holding the API key instead"
    )
    proxy_url = models.URLField(
        blank=True, help_text="Optional proxy URL used only when checking this provider's connectivity"
    )
    connection_timeout_seconds = models.PositiveIntegerField(default=10)

    panels = [
        MultiFieldPanel(
            [
                FieldPanel("name"),
                FieldPanel("slug"),
                FieldPanel("provider_type"),
                FieldPanel("is_active"),
                FieldPanel("is_default"),
                FieldPanel("sort_order"),
            ],
            heading="Identity",
        ),
        MultiFieldPanel(
            [
                FieldPanel("model_name"),
                FieldPanel("embedding_dimensions"),
                FieldPanel("best_use_case"),
                FieldPanel("performance_rating"),
                FieldPanel("cost_indicator"),
                FieldPanel("capability"),
            ],
            heading="Provider Details",
        ),
        MultiFieldPanel(
            [
                FieldPanel("highlights"),
                FieldPanel("why_choose"),
            ],
            heading="User Guidance",
        ),
        MultiFieldPanel(
            [
                FieldPanel("badge_recommended"),
                FieldPanel("badge_cost_effective"),
                FieldPanel("badge_fully_offline"),
                FieldPanel("badge_fastest"),
                FieldPanel("badge_highest_accuracy"),
            ],
            heading="Recommendation Badges",
        ),
        MultiFieldPanel(
            [
                FieldPanel("base_url"),
                FieldPanel("api_key"),
                FieldPanel("api_key_env_var"),
                FieldPanel("proxy_url"),
                FieldPanel("connection_timeout_seconds"),
            ],
            heading="Connection (optional)",
        ),
    ]

    class Meta:
        ordering = ["sort_order", "name"]
        verbose_name = "Embedding Profile"
        verbose_name_plural = "Embedding Profiles"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        if self.is_default:
            EmbeddingProfile.objects.filter(is_default=True).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)

    @property
    def badges(self):
        badge_map = [
            ("badge_recommended", "recommended", "Recommended", "\U0001F3C6"),
            ("badge_cost_effective", "cost_effective", "Cost Effective", "\U0001F4B0"),
            ("badge_fully_offline", "fully_offline", "Fully Offline", "\U0001F512"),
            ("badge_fastest", "fastest", "Fastest", "\u26A1"),
            ("badge_highest_accuracy", "highest_accuracy", "Highest Accuracy", "\U0001F3AF"),
        ]
        return [
            {"key": key, "label": label, "icon": icon}
            for field, key, label, icon in badge_map
            if getattr(self, field)
        ]

    # Providers whose availability check requires an API key to be meaningful.
    _KEY_REQUIRED_TYPES = {"openai", "azure_openai", "huggingface", "custom"}

    def get_api_key(self):
        if self.api_key:
            return self.api_key
        if not self.api_key_env_var:
            return ""
        return os.getenv(self.api_key_env_var, "")

    @property
    def is_configured(self):
        if self.provider_type == self.ProviderType.DEFAULT:
            return True
        if not self.base_url:
            return False
        if self.provider_type in self._KEY_REQUIRED_TYPES and not self.get_api_key():
            return False
        return True

    def test_connection(self, base_url=None, api_key=None, proxy_url=None, timeout_seconds=None):
        """Check whether this provider's endpoint is reachable.

        Accepts optional overrides so the configuration form can test values
        before they are saved. Proxy is always optional. Returns a "log" list
        of console-style lines so admins can see exactly what was sent and
        what came back when a provider fails to connect.
        """
        import time

        import httpx

        log = []

        def trace(line):
            log.append(f"[{time.strftime('%H:%M:%S')}] {line}")

        if self.provider_type == self.ProviderType.DEFAULT:
            trace("Default provider uses a built-in deterministic embedding.")
            trace("No network call is made - always available.")
            return {"available": True, "detail": "Built-in embedding - always available.", "latency_ms": 0, "log": log}

        target_url = base_url if base_url is not None else self.base_url
        trace(f"Provider: {self.name} ({self.get_provider_type_display()})")
        if not target_url:
            trace("No base URL configured - nothing to test.")
            return {"available": False, "detail": "No endpoint configured yet.", "latency_ms": 0, "log": log}

        target_key = api_key if api_key else self.get_api_key()
        target_proxy = proxy_url if proxy_url is not None else self.proxy_url
        target_timeout = timeout_seconds or self.connection_timeout_seconds or 10

        headers = {"Authorization": f"Bearer {target_key}"} if target_key else {}
        headers["Content-Type"] = "application/json"
        request_body = {}
        client_kwargs = {"timeout": target_timeout, "trust_env": False}
        if target_proxy:
            client_kwargs["proxy"] = target_proxy

        trace(f"POST {target_url}")
        trace(f"Proxy: {target_proxy or 'none'}")
        trace(f"Authorization header: {'Bearer ****' + target_key[-4:] if target_key else 'not sent (no API key)'}")
        trace(f"Timeout: {target_timeout}s")
        trace(f"Body: {request_body}")

        started = time.perf_counter()
        try:
            with httpx.Client(**client_kwargs) as client:
                response = client.post(target_url, headers=headers, json=request_body)
            latency_ms = int((time.perf_counter() - started) * 1000)
            trace(f"Response received in {latency_ms}ms")
            trace(f"Status: {response.status_code} {response.reason_phrase}")
            body_snippet = (response.text or "")[:300]
            if body_snippet:
                trace(f"Body: {body_snippet}")
            if response.status_code < 500:
                trace("Result: reachable (status below 500).")
                return {
                    "available": True,
                    "detail": f"Reachable (HTTP {response.status_code}).",
                    "latency_ms": latency_ms,
                    "log": log,
                }
            trace("Result: unavailable (server error).")
            return {
                "available": False,
                "detail": f"Endpoint returned HTTP {response.status_code}.",
                "latency_ms": latency_ms,
                "log": log,
            }
        except Exception as exc:
            latency_ms = int((time.perf_counter() - started) * 1000)
            trace(f"Request failed after {latency_ms}ms: {type(exc).__name__}: {exc}")
            trace("Result: unavailable (request error). Check the URL, API key, and proxy above.")
            return {"available": False, "detail": str(exc), "latency_ms": latency_ms, "log": log}

    def to_card_dict(self):
        return {
            "slug": self.slug,
            "name": self.name,
            "provider_type": self.provider_type,
            "provider_type_display": self.get_provider_type_display(),
            "model_name": self.model_name,
            "embedding_dimensions": self.embedding_dimensions,
            "best_use_case": self.best_use_case,
            "performance_rating": self.performance_rating,
            "cost_indicator": self.cost_indicator,
            "cost_indicator_display": self.get_cost_indicator_display(),
            "capability": self.capability,
            "capability_display": self.get_capability_display(),
            "highlights": self.highlights or [],
            "why_choose": self.why_choose,
            "badges": self.badges,
            "is_default": self.is_default,
            "is_configured": self.is_configured,
            "base_url": self.base_url,
            "api_key_set": bool(self.get_api_key()),
            "proxy_url": self.proxy_url,
            "connection_timeout_seconds": self.connection_timeout_seconds,
        }


@register_setting
class VectorDBSettings(BaseSiteSetting):
    """Vector DB selection settings shown under Wagtail Settings sidebar."""

    qdrant_url = models.URLField(blank=True, default="http://localhost:6333")
    qdrant_api_key = models.CharField(max_length=255, blank=True)
    qdrant_prefer_grpc = models.BooleanField(default=False)
    qdrant_timeout_seconds = models.PositiveIntegerField(default=30)

    default_qdrant_connection = models.ForeignKey(
        QdrantConnection,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="default_vector_db_settings",
    )
    default_knowledge_base = models.ForeignKey(
        KnowledgeBase,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="default_vector_kb_settings",
    )
    auto_create_collections = models.BooleanField(default=True)

    panels = [
        ReadOnlyPanel("enterprise_dashboard_display", heading=""),
    ]

    @property
    def runtime_help_display(self):
        return format_html(
            '<div style="padding: 12px; border: 1px solid #cfe2ff; background: #f4f8ff; border-radius: 8px;">'
            '<strong style="display:block; margin-bottom:6px; color:#1f3b73;">How to use this dashboard</strong>'
            '<ul style="margin:0; padding-left: 18px; color:#30486f; font-size:13px;">'
            '<li>Set Qdrant URL and API key once in this page.</li>'
            '<li>Use default knowledge base to control where uploads are indexed.</li>'
            '<li>Connection, collections, upload and recent documents are all visible below.</li>'
            '</ul>'
            '</div>'
        )

    def get_test_connection(self):
        from apps.knowledge.services.repository import QdrantRepository

        temp_conn = QdrantConnection(
            url=self.qdrant_url or "http://localhost:6333",
            api_key=self.qdrant_api_key or "",
            prefer_grpc=self.qdrant_prefer_grpc,
            timeout_seconds=self.qdrant_timeout_seconds or 30,
        )
        try:
            repo = QdrantRepository(temp_conn)
            repo.ping()
            collections = repo._get_client().get_collections().collections
            return {"connected": True, "collections": collections, "error": None}
        except Exception as exc:
            return {"connected": False, "collections": [], "error": str(exc)}

    @property
    def connection_status_display(self):
        result = self.get_test_connection()
        if result["connected"]:
            return format_html(
                '<div style="padding: 10px; background: #d4edda; border: 1px solid #c3e6cb; border-radius: 4px;">'
                '<span style="color: #28a745; font-size: 18px;">●</span> '
                '<strong style="color: #155724;">Connected to Qdrant</strong><br>'
                '<small style="color: #155724;">URL: {}</small>'
                '</div>',
                self.qdrant_url or "http://localhost:6333",
            )
        return format_html(
            '<div style="padding: 10px; background: #f8d7da; border: 1px solid #f5c6cb; border-radius: 4px;">'
            '<span style="color: #dc3545; font-size: 18px;">●</span> '
            '<strong style="color: #721c24;">Connection Failed</strong><br>'
            '<small style="color: #721c24;">{}</small>'
            '</div>',
            result["error"] or "Cannot reach Qdrant server",
        )

    @property
    def collections_display(self):
        result = self.get_test_connection()
        if not result["connected"]:
            return format_html(
                '<div style="padding: 10px; background: #fff3cd; border: 1px solid #ffeaa7; border-radius: 4px;">'
                '<em style="color: #856404;">Connect to Qdrant to see collections</em>'
                '</div>'
            )

        collections = result["collections"]
        if not collections:
            return format_html(
                '<div style="padding: 10px; background: #e2e3e5; border: 1px solid #d6d8db; border-radius: 4px;">'
                '<em style="color: #383d41;">No collections found in Qdrant</em>'
                '</div>'
            )

        collection_rows = "".join(
            [
                f'<tr style="border-bottom: 1px solid #dee2e6;">'
                f'<td style="padding: 8px;"><strong>{c.name}</strong></td>'
                f'<td style="padding: 8px; text-align: right;">{getattr(c, "points_count", "N/A")} points</td>'
                f'<td style="padding: 8px; text-align: right;">{getattr(c, "vectors_count", "N/A")} vectors</td>'
                f"</tr>"
                for c in collections
            ]
        )

        return format_html(
            '<div style="padding: 10px; background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 4px;">'
            '<strong style="color: #495057; margin-bottom: 8px; display: block;">Collections ({} total):</strong>'
            '<table style="width: 100%; border-collapse: collapse; background: white;">'
            '<thead><tr style="background: #e9ecef; border-bottom: 2px solid #dee2e6;">'
            '<th style="padding: 8px; text-align: left;">Collection Name</th>'
            '<th style="padding: 8px; text-align: right;">Points</th>'
            '<th style="padding: 8px; text-align: right;">Vectors</th>'
            '</tr></thead>'
            '<tbody>{}</tbody>'
            '</table>'
            '</div>',
            len(collections),
            mark_safe(collection_rows),
        )

    @property
    def upload_widget_display(self):
        kb_options = ['<option value="">Use default knowledge base</option>']
        for kb in KnowledgeBase.objects.filter(is_active=True).order_by("name"):
            kb_options.append(f'<option value="{kb.slug}">{kb.name} ({kb.slug})</option>')
        html = (
            '<div style="padding: 12px; border: 1px solid #dbe5f0; background: #fbfdff; border-radius: 8px;">'
            '<strong style="display:block; margin-bottom:8px; color:#253858;">Upload file and index to Qdrant</strong>'
            '<div style="display:grid; gap:8px;">'
            '<input id="vector-db-upload-file" type="file" style="padding:8px; border:1px solid #ccd8ea; border-radius:6px;" />'
            '<input id="vector-db-upload-title" type="text" placeholder="Optional title" style="padding:8px; border:1px solid #ccd8ea; border-radius:6px;" />'
            '<select id="vector-db-upload-kb" style="padding:8px; border:1px solid #ccd8ea; border-radius:6px;">'
            + "".join(kb_options)
            + '</select>'
            '<button type="button" id="vector-db-upload-btn" style="background:#0f5cc0; color:white; border:none; border-radius:6px; padding:10px 12px; font-weight:600; cursor:pointer;">Upload and Index</button>'
            '<div id="vector-db-upload-status" style="font-size:12px; color:#30486f;"></div>'
            '</div>'
            '<script>'
            '(function(){'
            'if (window.__vectorUploadInit) return;'
            'window.__vectorUploadInit = true;'
            'document.addEventListener("click", async function(event){'
            'if (!event.target || event.target.id !== "vector-db-upload-btn") return;'
            'const fileInput = document.getElementById("vector-db-upload-file");'
            'const titleInput = document.getElementById("vector-db-upload-title");'
            'const kbSelect = document.getElementById("vector-db-upload-kb");'
            'const status = document.getElementById("vector-db-upload-status");'
            'if (!fileInput || !fileInput.files || !fileInput.files.length) {'
            'status.textContent = "Please choose a file first.";'
            'status.style.color = "#b42318";'
            'return;'
            '}'
            'status.textContent = "Uploading and indexing in Qdrant...";'
            'status.style.color = "#1f3b73";'
            'const formData = new FormData();'
            'formData.append("file", fileInput.files[0]);'
            'if (titleInput && titleInput.value.trim()) formData.append("title", titleInput.value.trim());'
            'if (kbSelect && kbSelect.value) formData.append("knowledge_base_slug", kbSelect.value);'
            'try {'
            'const res = await fetch("/api/v1/upload-file/", { method: "POST", body: formData });'
            'const payload = await res.json();'
            'if (!res.ok) {'
            'status.textContent = payload.error || "Upload failed";'
            'status.style.color = "#b42318";'
            'return;'
            '}'
            'status.textContent = "Indexed. Job " + payload.job_id + ", chunks " + (payload.chunk_count || 0) + ", KB " + payload.knowledge_base + ". Refresh page to see it below.";'
            'status.style.color = "#18794e";'
            '} catch (err) {'
            'status.textContent = "Upload failed: " + err.message;'
            'status.style.color = "#b42318";'
            '}'
            '});'
            '})();'
            '</script>'
            '</div>'
        )
        return mark_safe(html)

    @property
    def uploaded_documents_display(self):
        from apps.ingestion.models import UploadedDocument

        documents_qs = UploadedDocument.objects.select_related("data_source__knowledge_base").order_by("-created_at")
        if self.default_knowledge_base_id:
            documents_qs = documents_qs.filter(data_source__knowledge_base_id=self.default_knowledge_base_id)

        documents = list(documents_qs[:10])
        if not documents:
            return format_html(
                '<div style="padding: 10px; background: #f8fafc; border: 1px dashed #c9d7eb; border-radius: 8px; color: #486284;">'
                'No uploaded documents found yet. Upload from the form above and they will appear here.'
                '</div>'
            )

        rows = []
        for doc in documents:
            latest_job = doc.jobs.order_by("-created_at").first()
            status = latest_job.status if latest_job else "-"
            chunk_count = latest_job.chunk_count if latest_job else 0
            kb_name = doc.data_source.knowledge_base.name if doc.data_source_id else "-"
            rows.append(
                f'<tr style="border-bottom: 1px solid #e3ebf5;">'
                f'<td style="padding:8px;">{escape(doc.title)}</td>'
                f'<td style="padding:8px;">{escape(kb_name)}</td>'
                f'<td style="padding:8px; text-transform:capitalize;">{escape(status)}</td>'
                f'<td style="padding:8px; text-align:right;">{chunk_count}</td>'
                f'<td style="padding:8px;">{doc.created_at.strftime("%Y-%m-%d %H:%M")}</td>'
                f'</tr>'
            )

        return format_html(
            '<div style="padding: 10px; background: #ffffff; border: 1px solid #d9e4f2; border-radius: 8px;">'
            '<strong style="display:block; margin-bottom:8px; color:#2a3f61;">Recent uploaded files indexed to Qdrant</strong>'
            '<table style="width:100%; border-collapse: collapse; font-size: 12px;">'
            '<thead><tr style="background:#f3f7fc;">'
            '<th style="padding:8px; text-align:left;">Title</th>'
            '<th style="padding:8px; text-align:left;">Knowledge Base</th>'
            '<th style="padding:8px; text-align:left;">Index Status</th>'
            '<th style="padding:8px; text-align:right;">Chunks</th>'
            '<th style="padding:8px; text-align:left;">Uploaded At</th>'
            '</tr></thead>'
            '<tbody>{}</tbody>'
            '</table>'
            '</div>',
            mark_safe("".join(rows)),
        )

    @property
    def enterprise_dashboard_display(self):
        connection_result = self.get_test_connection()
        connection_status = "Connected" if connection_result["connected"] else "Disconnected"
        connection_class = "vdbx-green" if connection_result["connected"] else "vdbx-red"
        connection_detail = self.qdrant_url or "http://localhost:6333"
        if connection_result["error"]:
            connection_detail = connection_result["error"]
        html = '''
<style>
    .vdbx-shell { background: #08111f !important; border-color: #20334b !important; border-radius: 10px !important; color: #e8eef7; box-shadow: 0 14px 36px rgba(6,16,29,.8); }
    .vdbx-top, .vdbx-nav, .vdbx-card, .vdbx-quick button, .vdbx-drop { background: #0d1a2b !important; border-color: #20334b !important; color: #e8eef7 !important; }
    .vdbx-top h3, .vdbx-card h4 { color: #e8eef7 !important; }
    .vdbx-top p, .vdbx-tip { color: #8da1ba !important; }
    .vdbx-tab { background: transparent !important; border-color: transparent !important; color: #a9b9cf !important; }
    .vdbx-tab.active, .vdbx-tab:hover { background: #24265c !important; border-color: #4f5be2 !important; color: #fff !important; }
    .vdbx-btn { background: #101e31 !important; border-color: #2a3d57 !important; color: #e8eef7 !important; }
    .vdbx-btn.primary { background: #5c51dd !important; border-color: #756aff !important; color: #fff !important; }
    .vdbx-value, .vdbx-name, .vdbx-table td { color: #e8eef7 !important; }
    .vdbx-table th { background: #111f32 !important; color: #8297b2 !important; border-color: #20334b !important; }
    .vdbx-table td, .vdbx-table tr { border-color: #192a40 !important; }
    .vdbx-input, .vdbx-select, .vdbx-textarea { background: #0a1727 !important; border-color: #2a3d57 !important; color: #fff !important; }
    .vdbx-progress { background: #1b2c43 !important; }
    .vdbx-progress > span { background: linear-gradient(90deg,#2bbf78,#60d58e) !important; }
    .vdbx-dashboard-grid { display:grid; grid-template-columns:1.25fr .8fr; gap:10px; }
    .vdbx-health-chart { height:130px; border-radius:7px; background:repeating-linear-gradient(to bottom,transparent 0,transparent 30px,#20334b 31px); position:relative; overflow:hidden; }
    .vdbx-health-line { position:absolute; inset:14px 8px; background:linear-gradient(155deg,transparent 0 15%,#2b94ef 16% 18%,transparent 19% 34%,#32c878 35% 37%,transparent 38% 57%,#f5b83d 58% 60%,transparent 61%); clip-path:polygon(0 70%,8% 45%,16% 55%,24% 35%,32% 48%,40% 28%,48% 42%,56% 23%,64% 36%,72% 18%,80% 31%,88% 20%,100% 34%,100% 100%,0 100%); }
    @media (max-width: 980px) { .vdbx-dashboard-grid { grid-template-columns:1fr; } }
    .vdbx-help-node, .vdbx-rca-item { background: #0e1d30 !important; border-color: #2a3d57 !important; color: #dce7f5 !important; }
    .vdbx-grid { min-height: 680px !important; }
</style>
<style>
.vdbx-shell { border: 1px solid #d8e2f0; background: #f5f8fc; border-radius: 12px; overflow: hidden; }
.vdbx-top { display:flex; align-items:center; justify-content:space-between; gap:10px; padding:12px 14px; background:#ffffff; border-bottom:1px solid #e2eaf4; }
.vdbx-top h3 { margin:0; font-size:16px; color:#1b2f4b; }
.vdbx-top p { margin:3px 0 0; font-size:12px; color:#5b708e; }
.vdbx-actions { display:flex; gap:8px; }
.vdbx-btn { border:1px solid #c6d5ea; background:#fff; color:#23406a; border-radius:7px; font-size:12px; font-weight:600; padding:7px 10px; cursor:pointer; }
.vdbx-btn.primary { background:#0f5cc0; border-color:#0f5cc0; color:#fff; }
    .vdbx-grid { display:block; min-height: 680px; }
    .vdbx-nav { display:none; }
.vdbx-tab { width:100%; text-align:left; margin-bottom:6px; padding:8px 10px; border:1px solid #d9e4f3; border-radius:8px; background:#fff; color:#2a456c; font-size:12px; font-weight:600; cursor:pointer; }
.vdbx-tab.active { background:#eaf2ff; border-color:#9ab8e8; color:#123a77; }
.vdbx-main { padding:12px; display:grid; gap:14px; }
    .vdbx-kpis { display:grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap:12px; }
.vdbx-card { border:1px solid #e6ebf3; border-radius:12px; background:#fff; box-shadow:0 1px 3px rgba(16,24,40,.05); }
.vdbx-card h4 { margin:0; font-size:13px; font-weight:700; color:#1e2f4a; padding:12px 14px; border-bottom:1px solid #eef2f8; letter-spacing:.01em; }
.vdbx-card .body { padding:14px; }
.vdbx-value { font-size:23px; font-weight:800; color:#0f335f; }
.vdbx-badge { display:inline-block; font-size:11px; padding:3px 8px; border-radius:999px; font-weight:700; text-transform:uppercase; }
.vdbx-green { background:#e2f7e8; color:#17663b; border:1px solid #b8e8c8; }
.vdbx-amber { background:#fff4dc; color:#8c5a08; border:1px solid #f2d59a; }
.vdbx-red { background:#ffe3e3; color:#8b1e24; border:1px solid #f3b4b9; }
.vdbx-gray { background:#eef2f7; color:#46576f; border:1px solid #d4dbe6; }
.vdbx-table { width:100%; border-collapse:collapse; font-size:12px; }
.vdbx-table th, .vdbx-table td { padding:8px; border-bottom:1px solid #e9eff7; text-align:left; vertical-align:top; }
.vdbx-table th { background:#f4f8ff; color:#395780; font-weight:700; }
.vdbx-list { margin:0; padding-left:18px; color:#2d4569; font-size:12px; }
.vdbx-tools { display:flex; flex-wrap:wrap; gap:8px; margin-bottom:8px; }
.vdbx-input, .vdbx-select, .vdbx-textarea { border:1px solid #c9d7ec; border-radius:8px; padding:8px; font-size:12px; width:100%; }
.vdbx-textarea { min-height:80px; resize:vertical; }
.vdbx-row2 { display:grid; grid-template-columns: 1fr 1fr; gap:10px; }
.vdbx-drop { border:2px dashed #abc3e5; border-radius:10px; background:#f8fbff; padding:18px; text-align:center; color:#355781; cursor:pointer; }
.vdbx-progress { width:100%; height:8px; border-radius:999px; background:#e6eef9; overflow:hidden; }
.vdbx-progress > span { display:block; height:100%; background:#1e67ca; width:0; }
.vdbx-help-flow { display:flex; flex-wrap:wrap; gap:8px; align-items:center; }
.vdbx-help-node { padding:8px 10px; border-radius:8px; border:1px solid #cfe0f8; background:#f7fbff; color:#1f406f; font-size:12px; font-weight:700; }
.vdbx-help-arrow { color:#5f7ea8; font-size:15px; font-weight:700; }
    .vdbx-pipeline { display:flex; gap:6px; align-items:center; }
    .vdbx-pipeline-step { flex:1; min-width:90px; padding:10px 8px; border:1px solid #20334b; border-radius:8px; background:#0e1d30; color:#e8eef7; font-size:11px; }
    .vdbx-pipeline-step strong { display:block; margin-bottom:5px; }
    .vdbx-pipeline-step span { color:#32c878; font-size:10px; }
    .vdbx-pipeline-arrow { color:#8da1ba; font-weight:700; }
    .vdbx-quick-actions { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:8px; margin:10px 0; }
    .vdbx-quick-actions button { text-align:left; padding:10px; border:1px solid #20334b; border-radius:8px; background:#0d1a2b; color:#e8eef7; cursor:pointer; }
    .vdbx-quick-actions strong { display:block; font-size:11px; }
    .vdbx-quick-actions small { color:#8da1ba; font-size:9px; }
.vdbx-tip { color:#5a6f8f; font-size:11px; }
    .vdbx-section { display:grid; gap:10px; }
    .vdbx-section.active { display:grid; gap:10px; }
@media (max-width: 980px) {
    .vdbx-grid { display:block; }
    .vdbx-kpis { grid-template-columns: repeat(3, minmax(0,1fr)); }
.vdbx-row2 { grid-template-columns: 1fr; }
    .vdbx-quick-actions { grid-template-columns:1fr 1fr; }
}
/* Keep the settings page light and focused on one visible workspace. */
.vdbx-shell { background:transparent !important; color:#162033 !important; box-shadow:none !important; border:0 !important; border-radius:0 !important; overflow:visible !important; }
.vdbx-top { background:transparent !important; border-bottom:0 !important; padding:0 0 12px !important; }
.vdbx-top > div:first-child { display:none !important; }
.vdbx-top, .vdbx-nav, .vdbx-card, .vdbx-quick-actions button, .vdbx-drop { background:#fff !important; color:#162033 !important; border-color:#d9e4f3 !important; }
.vdbx-top h3, .vdbx-card h4, .vdbx-value, .vdbx-table td { color:#1b2f4b !important; }
.vdbx-top p, .vdbx-tip { color:#5b708e !important; }
.vdbx-grid { display:grid !important; grid-template-columns:210px minmax(0,1fr) !important; min-height:680px !important; }
.vdbx-nav { display:block !important; padding:10px !important; border-right:1px solid #e2eaf4 !important; }
    .vdbx-sidebar-connection { margin-top:18px; padding:10px; border:1px solid #d9e4f3; border-radius:8px; background:#f7fbff; }
    .vdbx-sidebar-connection strong { display:block; margin-bottom:6px; color:#1b2f4b; font-size:12px; }
    .vdbx-sidebar-connection small { display:block; margin-top:6px; color:#5b708e; font-size:10px; line-height:1.35; word-break:break-word; }
.vdbx-section { display:none !important; }
.vdbx-section.active { display:grid !important; gap:10px !important; }
.vdbx-tab { background:#fff !important; color:#2a456c !important; border-color:#d9e4f3 !important; }
.vdbx-tab.active, .vdbx-tab:hover { background:#eaf2ff !important; border-color:#9ab8e8 !important; color:#123a77 !important; }
.vdbx-btn { background:#fff !important; color:#23406a !important; border-color:#c6d5ea !important; }
.vdbx-btn.primary { background:#0f5cc0 !important; color:#fff !important; }
.vdbx-table th { background:#f4f8ff !important; color:#395780 !important; border-color:#e9eff7 !important; }
.vdbx-table td, .vdbx-table tr { border-color:#e9eff7 !important; }
.vdbx-input, .vdbx-select, .vdbx-textarea { background:#fff !important; color:#162033 !important; border-color:#c9d7ec !important; }
.vdbx-pipeline-step { background:#f7fbff !important; color:#1f406f !important; border-color:#cfe0f8 !important; }
.vdbx-pipeline-step span { color:#17663b !important; }
@media (max-width:980px) { .vdbx-grid { grid-template-columns:1fr !important; } .vdbx-nav { border-right:0 !important; border-bottom:1px solid #e2eaf4 !important; } }
/* Polish pass: nicer cards, buttons, connection controls and modal dialog. */
.vdbx-card { box-shadow:0 1px 2px rgba(16,24,40,.04); transition:box-shadow .15s ease; }
.vdbx-card:hover { box-shadow:0 4px 14px rgba(16,24,40,.08); }
.vdbx-btn { transition:background .15s ease, border-color .15s ease, transform .05s ease; cursor:pointer; }
.vdbx-btn:hover { border-color:#9ab8e8; }
.vdbx-btn:active { transform:translateY(1px); }
.vdbx-btn.primary:hover { background:#0b4ca0 !important; }
.vdbx-tab { transition:background .15s ease, color .15s ease; }
.vdbx-quick-actions button { transition:box-shadow .15s ease, transform .05s ease; }
.vdbx-quick-actions button:hover { box-shadow:0 4px 14px rgba(16,24,40,.08); transform:translateY(-1px); }
.vdbx-table tbody tr:hover { background:#f7fbff; }
.vdbx-connection-link { display:flex; flex-direction:column; gap:4px; width:100%; text-align:left; background:#f7fbff !important; border:1px solid #d9e4f3 !important; border-radius:8px; padding:10px; margin-top:18px; cursor:pointer; }
.vdbx-connection-link strong { font-size:12px; color:#1b2f4b; }
.vdbx-connection-link small { color:#5b708e; font-size:10px; word-break:break-word; }
.vdbx-form-grid { display:grid; grid-template-columns:1fr 1fr; gap:12px; max-width:640px; }
.vdbx-form-grid label { display:flex; flex-direction:column; gap:5px; font-size:11px; color:#41546f; font-weight:600; }
.vdbx-form-grid .vdbx-full { grid-column:1/-1; }
.vdbx-checkbox-row { display:flex; align-items:center; gap:8px; font-size:12px; color:#41546f; }
.vdbx-checkbox-row input { width:auto; }
.vdbx-modal-overlay { position:fixed; inset:0; background:rgba(15,23,42,.45); display:none; align-items:center; justify-content:center; z-index:1000; padding:20px; }
.vdbx-modal-overlay.open { display:flex; }
.vdbx-modal { background:#fff; border-radius:12px; width:100%; max-width:460px; box-shadow:0 24px 60px rgba(15,23,42,.28); overflow:hidden; }
.vdbx-modal-head { padding:16px 18px; border-bottom:1px solid #eef1f7; display:flex; align-items:center; justify-content:space-between; }
.vdbx-modal-head h3 { margin:0; font-size:15px; color:#1b2f4b; }
.vdbx-modal-close { border:0; background:transparent; font-size:18px; color:#7a8aa3; cursor:pointer; line-height:1; }
.vdbx-modal-body { padding:18px; display:grid; gap:12px; max-height:70vh; overflow:auto; }
.vdbx-modal-body label { display:flex; flex-direction:column; gap:5px; font-size:11px; color:#41546f; font-weight:600; }
.vdbx-modal-foot { padding:14px 18px; border-top:1px solid #eef1f7; display:flex; justify-content:flex-end; gap:8px; }
.vdbx-modal-error { color:#b42318; font-size:12px; min-height:14px; }
.vdbx-kpi-card { display:flex; align-items:flex-start; gap:11px; border:1px solid #e6ebf3; border-radius:12px; background:linear-gradient(180deg,#ffffff,#fbfcfe); padding:14px; box-shadow:0 1px 3px rgba(16,24,40,.05); transition:box-shadow .15s ease, transform .12s ease; }
.vdbx-kpi-card:hover { box-shadow:0 8px 20px rgba(16,24,40,.10); transform:translateY(-2px); }
.vdbx-kpi-icon { flex:none; width:36px; height:36px; border-radius:10px; display:flex; align-items:center; justify-content:center; font-size:16px; font-weight:700; }
.vdbx-kpi-info { min-width:0; flex:1 1 auto; }
.vdbx-kpi-label { font-size:10.5px; font-weight:700; color:#6b7793; text-transform:uppercase; letter-spacing:.04em; margin-bottom:5px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.vdbx-kpi-value { font-size:21px; font-weight:800; color:#111a2c; line-height:1.2; margin-bottom:2px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.vdbx-kpi-sub { font-size:10.5px; color:#8894a8; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.vdbx-quick-actions button { display:flex; align-items:center; gap:10px; }
.vdbx-quick-actions button > span:last-child { display:flex; flex-direction:column; gap:2px; min-width:0; }
.vdbx-quick-icon { flex:none; width:30px; height:30px; border-radius:9px; background:#eaf1ff; color:#2a56c6; display:flex; align-items:center; justify-content:center; font-size:15px; font-weight:700; }
@media (max-width: 980px) { .vdbx-kpis { grid-template-columns: repeat(2, minmax(0,1fr)) !important; } .vdbx-quick-actions { grid-template-columns: repeat(2, minmax(0,1fr)) !important; } }
.vdbx-provider-grid { display:grid; grid-template-columns:repeat(auto-fit, minmax(230px, 1fr)); gap:12px; }
.vdbx-provider-card { border:1px solid #e6ebf3; border-radius:12px; background:#fff; padding:14px; box-shadow:0 1px 3px rgba(16,24,40,.05); transition:box-shadow .15s ease, border-color .15s ease; }
.vdbx-provider-card.selected { border-color:#2f6fed; box-shadow:0 0 0 3px rgba(47,111,237,.12); }
.vdbx-provider-head { display:flex; align-items:center; justify-content:space-between; gap:8px; margin-bottom:6px; }
.vdbx-provider-name { font-size:13px; font-weight:800; color:#132038; display:flex; align-items:center; gap:7px; }
.vdbx-status-dot { display:inline-block; width:9px; height:9px; border-radius:50%; flex:none; }
.vdbx-dot-green { background:#22c55e; box-shadow:0 0 0 3px rgba(34,197,94,.18); }
.vdbx-dot-red { background:#ef4444; box-shadow:0 0 0 3px rgba(239,68,68,.18); }
.vdbx-console { display:none; background:#0b1220; color:#a9f5b0; font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; font-size:11px; line-height:1.5; padding:12px; border-radius:8px; max-height:220px; overflow:auto; white-space:pre-wrap; word-break:break-word; margin:0; }
.vdbx-console.open { display:block; }
.vdbx-provider-model { font-size:10.5px; color:#7c8aa3; margin-bottom:8px; }
.vdbx-provider-badges { display:flex; flex-wrap:wrap; gap:5px; margin-bottom:8px; }
.vdbx-provider-badge { font-size:10px; font-weight:700; padding:3px 7px; border-radius:999px; background:#eef3ff; color:#2a4fb0; border:1px solid #d7e2fb; white-space:nowrap; }
.vdbx-provider-meta { display:grid; grid-template-columns:1fr 1fr; gap:6px; font-size:10.5px; color:#4d5d78; margin-bottom:8px; }
.vdbx-provider-meta strong { display:block; color:#8894a8; font-weight:700; font-size:9.5px; text-transform:uppercase; letter-spacing:.03em; }
.vdbx-stars { color:#f5a623; letter-spacing:1px; font-size:12px; }
.vdbx-provider-highlights { list-style:none; margin:0 0 8px; padding:0; display:grid; gap:4px; font-size:11px; color:#33455f; }
.vdbx-provider-highlights li { display:flex; gap:6px; align-items:flex-start; }
.vdbx-provider-why { font-size:11px; color:#5b6c88; background:#f7fbff; border:1px dashed #cfe0f8; border-radius:8px; padding:8px; display:none; }
.vdbx-provider-why.open { display:block; }
.vdbx-provider-why-toggle { border:0; background:transparent; color:#2a56c6; font-size:11px; font-weight:700; cursor:pointer; padding:0; }
.vdbx-provider-select-btn { width:100%; margin-top:8px; }
.vdbx-compare-table { width:100%; border-collapse:collapse; font-size:11px; }
.vdbx-compare-table th, .vdbx-compare-table td { border:1px solid #e9eff7; padding:8px; text-align:left; vertical-align:top; }
.vdbx-compare-table th { background:#f4f8ff; color:#395780; font-weight:700; }
</style>

<div class="vdbx-shell" id="vdbx-shell">
<div class="vdbx-top">
<div>
</div>
<div class="vdbx-actions">
    <button type="button" class="vdbx-btn" id="vdbx-refresh-all">Refresh All</button>
    <button type="button" class="vdbx-btn primary" id="vdbx-create-collection">Create Collection</button>
</div>
</div>

<div class="vdbx-grid">
<nav class="vdbx-nav" id="vdbx-nav">
    <button type="button" class="vdbx-tab active" data-target="dashboard" title="Overview and health">Dashboard</button>
    <button type="button" class="vdbx-tab" data-target="collections" title="Create, edit, delete collections">Collections Management</button>
    <button type="button" class="vdbx-tab" data-target="upload" title="Upload with drag and drop">Data Upload Center</button>
    <button type="button" class="vdbx-tab" data-target="sync" title="Connector status and re-sync">Data Source Sync</button>
    <button type="button" class="vdbx-tab" data-target="embedding" title="Embedding model and counters">Embedding Monitor</button>
    <button type="button" class="vdbx-tab" data-target="search" title="Semantic search playground">Search Playground</button>
    <button type="button" class="vdbx-tab" data-target="monitoring" title="Connectivity, growth, errors">System Monitoring</button>
    <button type="button" class="vdbx-tab" data-target="connection" title="View or change the Qdrant connection">Connection</button>
    <button type="button" class="vdbx-tab" data-target="help" title="How retrieval pipeline works">User Help</button>
    <button type="button" class="vdbx-connection-link" id="vdbx-connection-shortcut" data-target="connection">
        <strong>Qdrant Connection</strong>
        <span class="vdbx-badge __CONNECTION_CLASS__" id="vdbx-connection-badge">__CONNECTION_STATUS__</span>
        <small id="vdbx-connection-url">URL: __CONNECTION_DETAIL__</small>
    </button>
</nav>

<section class="vdbx-main">
    <div class="vdbx-section active" data-section="dashboard">
        <div class="vdbx-kpis" id="vdbx-kpis"></div>
        <div class="vdbx-quick-actions">
            <button type="button" data-quick="create"><span class="vdbx-quick-icon">+</span><span><strong>Create Collection</strong><small>New vector collection</small></span></button>
            <button type="button" data-quick="upload"><span class="vdbx-quick-icon">&#8679;</span><span><strong>Upload Data</strong><small>Index documents</small></span></button>
            <button type="button" data-quick="sync"><span class="vdbx-quick-icon">&#8644;</span><span><strong>Connect API</strong><small>Sync external data</small></span></button>
            <button type="button" data-quick="search"><span class="vdbx-quick-icon">&#9906;</span><span><strong>Search Playground</strong><small>Test vector search</small></span></button>
        </div>
        <div class="vdbx-card">
            <h4>Ingestion and Embedding Pipeline</h4>
            <div class="body">
                <div class="vdbx-pipeline">
                    <div class="vdbx-pipeline-step"><strong>Document</strong><span>Ready</span></div><span class="vdbx-pipeline-arrow">-&gt;</span>
                    <div class="vdbx-pipeline-step"><strong>Chunking</strong><span id="vdbx-pipeline-chunks">Live</span></div><span class="vdbx-pipeline-arrow">-&gt;</span>
                    <div class="vdbx-pipeline-step"><strong>Embedding</strong><span>Ready</span></div><span class="vdbx-pipeline-arrow">-&gt;</span>
                    <div class="vdbx-pipeline-step"><strong>Qdrant Upsert</strong><span>Ready</span></div>
                </div>
                <div class="vdbx-progress" style="margin-top:10px;"><span id="vdbx-pipeline-progress"></span></div>
            </div>
        </div>
        <div class="vdbx-dashboard-grid">
            <div class="vdbx-card"><h4>Collections Overview</h4><div class="body" id="vdbx-collections-overview">Loading collections...</div></div>
            <div class="vdbx-card"><h4>System Health</h4><div class="body"><div class="vdbx-health-chart"><div class="vdbx-health-line"></div></div><div class="vdbx-tip" style="margin-top:7px;">Qdrant connectivity and collection health are live from monitoring.</div></div></div>
        </div>
        <div class="vdbx-card">
            <h4>Recent Activities</h4>
            <div class="body"><div id="vdbx-activities" class="vdbx-tip">Loading activities...</div></div>
        </div>
    </div>

    <div class="vdbx-section" data-section="collections">
        <div class="vdbx-tools">
            <button type="button" class="vdbx-btn" id="vdbx-collections-refresh">Refresh</button>
        </div>
        <div class="vdbx-card">
            <h4>Collections Table</h4>
            <div class="body" id="vdbx-collections-table">Loading collections...</div>
        </div>
    </div>

    <div class="vdbx-section" data-section="upload">
        <div class="vdbx-card">
            <h4>Upload Files (Drag and Drop)</h4>
            <div class="body">
                <div class="vdbx-drop" id="vdbx-dropzone">Drop file here or click to choose</div>
                <input type="file" id="vdbx-file-input" style="display:none;" />
                <div class="vdbx-row2" style="margin-top:8px;">
                    <input class="vdbx-input" id="vdbx-upload-title" placeholder="Optional title" />
                    <label style="display:flex; flex-direction:column; gap:5px; font-size:11px; color:#41546f; font-weight:600;">Upload to collection
                        <select class="vdbx-select" id="vdbx-upload-kb"><option value="">Use default collection</option></select>
                    </label>
                </div>
                <div class="vdbx-row2" style="margin-top:8px;">
                    <label style="display:flex; flex-direction:column; gap:5px; font-size:11px; color:#41546f; font-weight:600;">Embedding Profile <span class="vdbx-tip">(optional)</span>
                        <select class="vdbx-select" id="vdbx-upload-embedding"><option value="">Use default embedding</option></select>
                    </label>
                    <div style="display:flex; align-items:flex-end;">
                        <button type="button" class="vdbx-btn" id="vdbx-compare-providers" style="width:100%;">Compare Providers</button>
                    </div>
                </div>
                <div style="margin-top:8px;" class="vdbx-progress"><span id="vdbx-upload-progress"></span></div>
                <div id="vdbx-upload-status" class="vdbx-tip" style="margin-top:6px;">Waiting for upload.</div>
            </div>
        </div>
        <div class="vdbx-card">
            <h4>Embedding Providers</h4>
            <div class="body">
                <p class="vdbx-tip" style="margin:0 0 10px;">Leave the default selected unless you have a reason to change it - existing uploads keep working exactly as before.</p>
                <div class="vdbx-provider-grid" id="vdbx-provider-cards">Loading embedding providers...</div>
            </div>
        </div>
        <div class="vdbx-card">
            <h4>Processing Status</h4>
            <div class="body" id="vdbx-upload-jobs">Loading upload jobs...</div>
        </div>
    </div>

    <div class="vdbx-section" data-section="sync">
        <div class="vdbx-card">
            <h4>API Connections and Sync Status</h4>
            <div class="body" id="vdbx-sync-connectors">Loading connectors...</div>
        </div>
        <div class="vdbx-card">
            <h4>Sync History</h4>
            <div class="body" id="vdbx-sync-history">Loading sync history...</div>
        </div>
    </div>

    <div class="vdbx-section" data-section="embedding">
        <div class="vdbx-card">
            <h4>Embedding Monitor</h4>
            <div class="body" id="vdbx-embedding-monitor">Loading embedding monitor...</div>
        </div>
    </div>

    <div class="vdbx-section" data-section="search">
        <div class="vdbx-card">
            <h4>Search Playground</h4>
            <div class="body">
                <div class="vdbx-row2">
                    <input class="vdbx-input" id="vdbx-search-query" placeholder="Enter semantic query" />
                    <input class="vdbx-input" id="vdbx-search-kb" placeholder="Knowledge base slug (optional)" />
                </div>
                <div class="vdbx-row2" style="margin-top:8px;">
                    <input class="vdbx-input" id="vdbx-search-topk" value="5" placeholder="Top K" />
                    <input class="vdbx-input" id="vdbx-search-threshold" placeholder="Score threshold optional" />
                </div>
                <div class="vdbx-tools" style="margin-top:8px;">
                    <button type="button" class="vdbx-btn primary" id="vdbx-search-run">Run Search</button>
                </div>
                <div id="vdbx-search-results" class="vdbx-tip">No query executed yet.</div>
            </div>
        </div>
    </div>

    <div class="vdbx-section" data-section="monitoring">
        <div class="vdbx-card">
            <h4>System Monitoring</h4>
            <div class="body" id="vdbx-monitoring">Loading system monitoring...</div>
        </div>
    </div>

    <div class="vdbx-section" data-section="connection">
        <div class="vdbx-card">
            <h4>Qdrant Connection</h4>
            <div class="body">
                <p class="vdbx-tip" style="margin:0 0 10px;">If your Qdrant instance runs somewhere else, update the URL below and click Test Connection before saving.</p>
                <div id="vdbx-connection-status" class="vdbx-tip">Checking connection...</div>
                <div class="vdbx-form-grid" style="margin-top:12px;">
                    <label class="vdbx-full">Qdrant URL
                        <input class="vdbx-input" id="vdbx-conn-url" placeholder="http://localhost:6333" />
                    </label>
                    <label>API Key
                        <input class="vdbx-input" id="vdbx-conn-key" placeholder="Leave blank to keep current key" />
                    </label>
                    <label>Timeout (seconds)
                        <input class="vdbx-input" id="vdbx-conn-timeout" value="30" />
                    </label>
                    <label class="vdbx-full">Default Knowledge Base
                        <select class="vdbx-select" id="vdbx-conn-default-kb"><option value="">No default</option></select>
                    </label>
                    <label class="vdbx-full">
                        <span class="vdbx-checkbox-row"><input type="checkbox" id="vdbx-conn-grpc" /> Prefer gRPC</span>
                    </label>
                </div>
                <div class="vdbx-tools" style="margin-top:12px;">
                    <button type="button" class="vdbx-btn" id="vdbx-conn-test">Test Connection</button>
                    <button type="button" class="vdbx-btn primary" id="vdbx-conn-save">Save Connection</button>
                </div>
            </div>
        </div>
    </div>

    <div class="vdbx-section" data-section="help">
        <div class="vdbx-card">
            <h4>Pipeline Visual Help</h4>
            <div class="body">
                <div class="vdbx-help-flow">
                    <span class="vdbx-help-node" title="Raw file or document source">Document</span>
                    <span class="vdbx-help-arrow">↓</span>
                    <span class="vdbx-help-node" title="Split into semantically useful passages">Chunking</span>
                    <span class="vdbx-help-arrow">↓</span>
                    <span class="vdbx-help-node" title="Convert chunks into vectors">Embedding</span>
                    <span class="vdbx-help-arrow">↓</span>
                    <span class="vdbx-help-node" title="Persist vectors and metadata">Qdrant Storage</span>
                    <span class="vdbx-help-arrow">↓</span>
                    <span class="vdbx-help-node" title="Retrieve nearest chunks">Semantic Search</span>
                </div>
                <ul class="vdbx-list" style="margin-top:10px;">
                    <li>Green badges indicate healthy operation.</li>
                    <li>Amber indicates degraded or missing expected data.</li>
                    <li>Red indicates failure or disconnection.</li>
                    <li>Use Dashboard for quick posture, then drill into specific modules.</li>
                </ul>
            </div>
        </div>
    </div>
</section>
</div>
</div>

<div class="vdbx-modal-overlay" id="vdbx-collection-modal">
    <div class="vdbx-modal">
        <div class="vdbx-modal-head">
            <h3 id="vdbx-modal-title">Create Collection</h3>
            <button type="button" class="vdbx-modal-close" id="vdbx-modal-close">&times;</button>
        </div>
        <div class="vdbx-modal-body">
            <label>Collection name
                <input class="vdbx-input" id="vdbx-modal-name" placeholder="e.g. Customer Support Docs" />
            </label>
            <label>Collection key <span class="vdbx-tip">(letters, numbers, underscore - leave blank to auto-generate)</span>
                <input class="vdbx-input" id="vdbx-modal-key" placeholder="customer_support_docs" />
            </label>
            <label>Vector dimension
                <input class="vdbx-input" id="vdbx-modal-dimension" value="1536" />
            </label>
            <label>Similarity threshold (0-1)
                <input class="vdbx-input" id="vdbx-modal-threshold" value="0.7" />
            </label>
            <label>Top K results
                <input class="vdbx-input" id="vdbx-modal-topk" value="5" />
            </label>
            <div class="vdbx-modal-error" id="vdbx-modal-error"></div>
        </div>
        <div class="vdbx-modal-foot">
            <button type="button" class="vdbx-btn" id="vdbx-modal-cancel">Cancel</button>
            <button type="button" class="vdbx-btn primary" id="vdbx-modal-submit">Create Collection</button>
        </div>
    </div>
</div>

<div class="vdbx-modal-overlay" id="vdbx-compare-modal">
    <div class="vdbx-modal" style="max-width:820px;">
        <div class="vdbx-modal-head">
            <h3>Compare Embedding Providers</h3>
            <button type="button" class="vdbx-modal-close" id="vdbx-compare-close">&times;</button>
        </div>
        <div class="vdbx-modal-body" id="vdbx-compare-body">Loading comparison...</div>
        <div class="vdbx-modal-foot">
            <button type="button" class="vdbx-btn primary" id="vdbx-compare-done">Done</button>
        </div>
    </div>
</div>

<div class="vdbx-modal-overlay" id="vdbx-provider-conn-modal">
    <div class="vdbx-modal">
        <div class="vdbx-modal-head">
            <h3 id="vdbx-provider-conn-title">Configure Provider</h3>
            <button type="button" class="vdbx-modal-close" id="vdbx-provider-conn-close">&times;</button>
        </div>
        <div class="vdbx-modal-body">
            <label>Base URL
                <input class="vdbx-input" id="vdbx-provider-conn-url" placeholder="https://api.example.com/v1" />
            </label>
            <label>API Key <span class="vdbx-tip">(leave blank to keep current key)</span>
                <input class="vdbx-input" id="vdbx-provider-conn-key" placeholder="Leave blank to keep current key" />
            </label>
            <label>Proxy URL <span class="vdbx-tip">(optional)</span>
                <input class="vdbx-input" id="vdbx-provider-conn-proxy" placeholder="http://proxy.company.com:8080 (optional)" />
            </label>
            <label>Timeout (seconds)
                <input class="vdbx-input" id="vdbx-provider-conn-timeout" value="10" />
            </label>
            <div id="vdbx-provider-conn-status" class="vdbx-tip">Not tested yet.</div>
            <div class="vdbx-modal-error" id="vdbx-provider-conn-error"></div>
            <pre class="vdbx-console" id="vdbx-provider-conn-console">Click "Console" to run a diagnostic request and see exactly what is sent and received.</pre>
        </div>
        <div class="vdbx-modal-foot">
            <button type="button" class="vdbx-btn" id="vdbx-provider-conn-console-btn">Console</button>
            <button type="button" class="vdbx-btn" id="vdbx-provider-conn-test">Test Connection</button>
            <button type="button" class="vdbx-btn primary" id="vdbx-provider-conn-save">Save</button>
        </div>
    </div>
</div>

<script>
(function(){
const shell = document.getElementById("vdbx-shell");
if (!shell) return;

const tabs = shell.querySelectorAll(".vdbx-tab");
const sections = shell.querySelectorAll(".vdbx-section");

function badgeClass(status) {
const s = String(status || "").toLowerCase();
if (s.includes("success") || s.includes("connected") || s.includes("green")) return "vdbx-green";
if (s.includes("failed") || s.includes("error") || s.includes("red") || s.includes("disconnect")) return "vdbx-red";
if (s.includes("running") || s.includes("pending") || s.includes("amber") || s.includes("warn")) return "vdbx-amber";
return "vdbx-gray";
}

async function api(url, options) {
    const requestOptions = options || {};
    requestOptions.headers = Object.assign({}, requestOptions.headers || {});
    const csrfCookie = document.cookie.split('; ').find((item) => item.indexOf('csrftoken=') === 0);
    if (csrfCookie) {
        requestOptions.headers['X-CSRFToken'] = decodeURIComponent(csrfCookie.split('=')[1]);
    }
    const res = await fetch(url, requestOptions);
let payload = {};
try { payload = await res.json(); } catch (_e) { payload = {}; }
if (!res.ok) throw new Error(payload.error || ("Request failed: " + res.status));
return payload;
}

function setActive(target) {
tabs.forEach((tab) => tab.classList.toggle("active", tab.getAttribute("data-target") === target));
sections.forEach((sec) => sec.classList.toggle("active", sec.getAttribute("data-section") === target));
}

tabs.forEach((tab) => {
tab.addEventListener("click", (event) => {
    event.preventDefault();
    const target = tab.getAttribute("data-target");
    setActive(target);
});
});

shell.querySelectorAll("[data-quick]").forEach((button) => {
button.addEventListener("click", () => {
    const target = button.getAttribute("data-quick");
    if (target === "create") createCollectionFlow();
    else setActive(target);
});
});

async function loadDashboard() {
const kpiEl = document.getElementById("vdbx-kpis");
const actEl = document.getElementById("vdbx-activities");
try {
    const data = await api("/api/v1/vector-db/dashboard/");
    const d = data.dashboard || {};
    const status = String(d.qdrant_status || "unknown");
    const kpiDefs = [
        {k:"Collections", v:d.total_collections || 0, sub:"Total Collections", icon:"&#9638;", color:"#2f6fed"},
        {k:"Vectors", v:d.total_vectors || 0, sub:"Total Vectors", icon:"&#9670;", color:"#7c3aed"},
        {k:"Documents", v:d.total_documents || 0, sub:"Total Documents", icon:"&#9636;", color:"#0891b2"},
        {k:"Chunks", v:d.total_chunks || 0, sub:"Indexed Chunks", icon:"&#9642;", color:"#d97706"},
        {k:"Storage", v:"Live", sub:"Qdrant Storage", icon:"&#9679;", color:"#059669"},
        {k:"Status", v:status, sub:"Connection Health", icon:"&#9889;", color: status === "connected" ? "#16a34a" : "#dc2626", badge:true}
    ];
    kpiEl.innerHTML = kpiDefs.map((x) =>
        '<div class="vdbx-kpi-card">' +
            '<div class="vdbx-kpi-icon" style="background:' + x.color + '1a; color:' + x.color + ';">' + x.icon + '</div>' +
            '<div class="vdbx-kpi-info">' +
                '<div class="vdbx-kpi-label">' + x.k + '</div>' +
                (x.badge ? '<span class="vdbx-badge ' + badgeClass(x.v) + '">' + x.v + '</span>' : '<div class="vdbx-kpi-value">' + x.v + '</div>') +
                '<div class="vdbx-kpi-sub">' + x.sub + '</div>' +
            '</div>' +
        '</div>'
    ).join("");

    const acts = d.recent_activities || [];
    if (!acts.length) {
        actEl.innerHTML = '<span class="vdbx-tip">No recent activities.</span>';
    } else {
        actEl.innerHTML = '<ul class="vdbx-list">' + acts.slice(0, 20).map((a) =>
            '<li><strong>' + (a.label || '-') + '</strong> <span class="vdbx-badge ' + badgeClass(a.status) + '">' + (a.status || 'info') + '</span> ' +
            '<span class="vdbx-tip">' + (a.timestamp || '') + '</span></li>'
        ).join('') + '</ul>';
    }
} catch (err) {
    kpiEl.innerHTML = '<div class="vdbx-card"><div class="body"><span class="vdbx-badge vdbx-red">Error</span> ' + err.message + '</div></div>';
    actEl.textContent = 'Unable to load activities: ' + err.message;
}
}

async function loadCollections() {
const table = document.getElementById("vdbx-collections-table");
try {
    const data = await api("/api/v1/vector-db/collections/");
    const rows = data.results || [];
    if (!rows.length) {
        table.innerHTML = '<span class="vdbx-tip">No collections found.</span>';
        return;
    }
    table.innerHTML = '<table class="vdbx-table"><thead><tr>' +
        '<th>Collection</th><th>Health</th><th>Vectors</th><th>Docs</th><th>Dimension</th><th>Actions</th>' +
        '</tr></thead><tbody>' +
        rows.map((r) =>
            '<tr>' +
            '<td><strong>' + (r.collection || '-') + '</strong><br><span class="vdbx-tip">KB: ' + (r.knowledge_base_slug || '-') + '</span></td>' +
            '<td><span class="vdbx-badge ' + badgeClass(r.health) + '">' + (r.health || 'unknown') + '</span></td>' +
            '<td>' + (r.vectors_count || 0) + '</td>' +
            '<td>' + (r.points_count || 0) + '</td>' +
            '<td>' + (r.vector_size || '-') + '</td>' +
            '<td>' +
                '<button class="vdbx-btn" data-action="stats" data-slug="' + (r.knowledge_base_slug || '') + '">Stats</button> ' +
                '<button class="vdbx-btn" data-action="edit" data-slug="' + (r.knowledge_base_slug || '') + '">Edit</button> ' +
                '<button class="vdbx-btn" data-action="delete" data-slug="' + (r.knowledge_base_slug || '') + '">Delete</button>' +
            '</td>' +
            '</tr>'
        ).join('') + '</tbody></table>';
    const overview = document.getElementById("vdbx-collections-overview");
    if (overview) overview.innerHTML = table.innerHTML;
} catch (err) {
    table.innerHTML = '<span class="vdbx-badge vdbx-red">Error</span> ' + err.message;
}
}

const modalOverlay = document.getElementById("vdbx-collection-modal");
const modalTitle = document.getElementById("vdbx-modal-title");
const modalName = document.getElementById("vdbx-modal-name");
const modalKey = document.getElementById("vdbx-modal-key");
const modalDimension = document.getElementById("vdbx-modal-dimension");
const modalThreshold = document.getElementById("vdbx-modal-threshold");
const modalTopK = document.getElementById("vdbx-modal-topk");
const modalError = document.getElementById("vdbx-modal-error");
const modalSubmit = document.getElementById("vdbx-modal-submit");
let modalMode = "create";
let modalSlug = null;

function openModal(mode, prefill) {
    modalMode = mode;
    modalSlug = (prefill && prefill.slug) || null;
    modalError.textContent = "";
    modalTitle.textContent = mode === "edit" ? "Edit Collection" : "Create Collection";
    modalSubmit.textContent = mode === "edit" ? "Save Changes" : "Create Collection";
    modalName.value = (prefill && prefill.name) || "";
    modalKey.value = (prefill && prefill.collection_name) || "";
    modalKey.disabled = mode === "edit";
    modalDimension.value = (prefill && prefill.vector_size) || "1536";
    modalDimension.disabled = mode === "edit";
    modalThreshold.value = (prefill && prefill.similarity_threshold) || "0.7";
    modalTopK.value = (prefill && prefill.top_k) || "5";
    modalOverlay.classList.add("open");
    modalName.focus();
}

function closeModal() {
    modalOverlay.classList.remove("open");
}

async function submitModal() {
    const name = modalName.value.trim();
    if (!name) {
        modalError.textContent = "Collection name is required.";
        return;
    }
    modalError.textContent = "";
    modalSubmit.disabled = true;
    modalSubmit.textContent = "Saving...";
    try {
        if (modalMode === "create") {
            await api("/api/v1/vector-db/collections/", {
                method: "POST",
                headers: {"Content-Type":"application/json"},
                body: JSON.stringify({
                    name,
                    collection_name: modalKey.value.trim(),
                    vector_size: Number(modalDimension.value || "1536"),
                    similarity_threshold: Number(modalThreshold.value || "0.7"),
                    top_k: Number(modalTopK.value || "5"),
                }),
            });
        } else {
            await api("/api/v1/vector-db/collections/" + modalSlug + "/", {
                method: "PATCH",
                headers: {"Content-Type":"application/json"},
                body: JSON.stringify({
                    name,
                    top_k: Number(modalTopK.value || "5"),
                    similarity_threshold: Number(modalThreshold.value || "0.7"),
                }),
            });
        }
        closeModal();
        await Promise.all([loadDashboard(), loadCollections()]);
    } catch (err) {
        modalError.textContent = err.message;
    } finally {
        modalSubmit.disabled = false;
        modalSubmit.textContent = modalMode === "edit" ? "Save Changes" : "Create Collection";
    }
}

function createCollectionFlow() {
    openModal("create", null);
}

document.getElementById("vdbx-modal-close").addEventListener("click", closeModal);
document.getElementById("vdbx-modal-cancel").addEventListener("click", closeModal);
document.getElementById("vdbx-modal-submit").addEventListener("click", submitModal);
modalOverlay.addEventListener("click", (event) => { if (event.target === modalOverlay) closeModal(); });

async function collectionAction(action, slug) {
if (!slug) return;
try {
    if (action === "stats") {
        const data = await api("/api/v1/vector-db/collections/" + slug + "/");
        window.alert("Collection: " + data.collection + "\\nPoints: " + ((data.stats || {}).points_count || 0) + "\\nVectors: " + ((data.stats || {}).vectors_count || 0));
        return;
    }
    if (action === "edit") {
        const data = await api("/api/v1/vector-db/collections/" + slug + "/");
        openModal("edit", {
            slug,
            name: data.name,
            collection_name: data.collection,
            vector_size: data.vector_size,
            top_k: data.top_k,
            similarity_threshold: data.similarity_threshold,
        });
        return;
    }
    if (action === "delete") {
        if (!window.confirm("Delete collection and knowledge base " + slug + "?")) return;
        await api("/api/v1/vector-db/collections/" + slug + "/", { method: "DELETE" });
    }
    await Promise.all([loadDashboard(), loadCollections()]);
} catch (err) {
    window.alert(action + " failed: " + err.message);
}
}

async function loadUploads() {
const jobsEl = document.getElementById("vdbx-upload-jobs");
try {
    const data = await api("/api/v1/vector-db/uploads/status/");
    const rows = data.results || [];
    if (!rows.length) {
        jobsEl.innerHTML = '<span class="vdbx-tip">No upload jobs found.</span>';
        return;
    }
    jobsEl.innerHTML = '<table class="vdbx-table"><thead><tr><th>Document</th><th>KB</th><th>Status</th><th>Chunks</th><th>Started</th></tr></thead><tbody>' +
        rows.map((r) => '<tr><td>' + (r.document || '-') + '</td><td>' + (r.knowledge_base || '-') + '</td><td><span class="vdbx-badge ' + badgeClass(r.status) + '">' + (r.status || '-') + '</span></td><td>' + (r.chunk_count || 0) + '</td><td>' + (r.started_at || '-') + '</td></tr>').join('') +
        '</tbody></table>';
} catch (err) {
    jobsEl.innerHTML = '<span class="vdbx-badge vdbx-red">Error</span> ' + err.message;
}
}

function bindUpload() {
const zone = document.getElementById("vdbx-dropzone");
const input = document.getElementById("vdbx-file-input");
const titleEl = document.getElementById("vdbx-upload-title");
const kbEl = document.getElementById("vdbx-upload-kb");
const embeddingEl = document.getElementById("vdbx-upload-embedding");
const status = document.getElementById("vdbx-upload-status");
const progress = document.getElementById("vdbx-upload-progress");

function send(file) {
    if (!file) return;
    const form = new FormData();
    form.append("file", file);
    if (titleEl.value.trim()) form.append("title", titleEl.value.trim());
    if (kbEl.value.trim()) form.append("knowledge_base_slug", kbEl.value.trim());
    if (embeddingEl && embeddingEl.value.trim()) form.append("embedding_profile_slug", embeddingEl.value.trim());

    const xhr = new XMLHttpRequest();
    xhr.open("POST", "/api/v1/upload-file/");
            const csrfCookie = document.cookie.split('; ').find((item) => item.indexOf('csrftoken=') === 0);
            if (csrfCookie) {
                xhr.setRequestHeader("X-CSRFToken", decodeURIComponent(csrfCookie.split('=')[1]));
            }
    xhr.upload.onprogress = function(e) {
        if (!e.lengthComputable) return;
        const pct = Math.max(2, Math.floor((e.loaded / e.total) * 100));
        progress.style.width = pct + "%";
    };
    xhr.onload = async function() {
        try {
            const payload = JSON.parse(xhr.responseText || "{}");
            if (xhr.status >= 200 && xhr.status < 300) {
                status.textContent = "Upload complete. Job " + payload.job_id + ", chunks " + (payload.chunk_count || 0) + ".";
                status.style.color = "#17663b";
                await Promise.all([loadDashboard(), loadUploads()]);
            } else {
                status.textContent = payload.error || "Upload failed";
                status.style.color = "#8b1e24";
            }
        } catch (_e) {
            status.textContent = "Upload failed.";
            status.style.color = "#8b1e24";
        }
    };
    xhr.onerror = function() {
        status.textContent = "Upload failed due to network issue.";
        status.style.color = "#8b1e24";
    };

    progress.style.width = "4%";
    status.textContent = "Uploading and indexing...";
    status.style.color = "#224774";
    xhr.send(form);
}

zone.addEventListener("click", () => input.click());
input.addEventListener("change", () => send(input.files && input.files[0]));
zone.addEventListener("dragover", (e) => { e.preventDefault(); zone.style.background = "#eef5ff"; });
zone.addEventListener("dragleave", () => { zone.style.background = "#f8fbff"; });
zone.addEventListener("drop", (e) => {
    e.preventDefault();
    zone.style.background = "#f8fbff";
    const file = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0];
    send(file);
});
}

async function loadSync() {
const conn = document.getElementById("vdbx-sync-connectors");
const hist = document.getElementById("vdbx-sync-history");
try {
    const data = await api("/api/v1/vector-db/sync/status/");
    const connectors = data.connectors || [];
    const history = data.sync_history || [];

    if (!connectors.length) {
        conn.innerHTML = '<span class="vdbx-tip">No active connectors.</span>';
    } else {
        conn.innerHTML = '<table class="vdbx-table"><thead><tr><th>Connector</th><th>Type</th><th>Status</th><th>Last Sync</th><th>Action</th></tr></thead><tbody>' +
            connectors.map((c) => '<tr>' +
                '<td>' + c.name + '</td>' +
                '<td>' + c.connector_type + '</td>' +
                '<td><span class="vdbx-badge ' + badgeClass(c.last_sync_status || 'gray') + '">' + (c.last_sync_status || 'unknown') + '</span></td>' +
                '<td>' + (c.last_sync_time || '-') + '</td>' +
                '<td><button class="vdbx-btn" data-resync="' + c.connector_id + '">Manual Re-Sync</button></td>' +
            '</tr>').join('') + '</tbody></table>';
    }

    if (!history.length) {
        hist.innerHTML = '<span class="vdbx-tip">No sync history.</span>';
    } else {
        hist.innerHTML = '<table class="vdbx-table"><thead><tr><th>Connector</th><th>Status</th><th>Fetched</th><th>Indexed</th><th>Time</th></tr></thead><tbody>' +
            history.map((h) => '<tr><td>' + h.connector + '</td><td><span class="vdbx-badge ' + badgeClass(h.status) + '">' + h.status + '</span></td><td>' + (h.fetched_count || 0) + '</td><td>' + (h.indexed_count || 0) + '</td><td>' + (h.created_at || '-') + '</td></tr>').join('') +
            '</tbody></table>';
    }
} catch (err) {
    conn.innerHTML = '<span class="vdbx-badge vdbx-red">Error</span> ' + err.message;
    hist.innerHTML = '<span class="vdbx-badge vdbx-red">Error</span> ' + err.message;
}
}

async function loadEmbedding() {
const el = document.getElementById("vdbx-embedding-monitor");
try {
    const data = await api("/api/v1/vector-db/embeddings/monitor/");
    const rows = data.results || [];
    if (!rows.length) {
        el.innerHTML = '<span class="vdbx-tip">No embedding metrics yet.</span>';
        return;
    }
    el.innerHTML = '<table class="vdbx-table"><thead><tr><th>KB</th><th>Model</th><th>Chunk Count</th><th>Dimension</th><th>Status</th><th>Success</th><th>Failed</th></tr></thead><tbody>' +
        rows.map((r) => '<tr><td>' + r.knowledge_base + '</td><td>' + r.embedding_model + '</td><td>' + r.chunk_count + '</td><td>' + r.embedding_dimension + '</td><td><span class="vdbx-badge ' + badgeClass(r.processing_status) + '">' + r.processing_status + '</span></td><td>' + r.success_count + '</td><td>' + r.failed_count + '</td></tr>').join('') +
        '</tbody></table>';
} catch (err) {
    el.innerHTML = '<span class="vdbx-badge vdbx-red">Error</span> ' + err.message;
}
}

async function runSearch() {
const q = document.getElementById("vdbx-search-query").value.trim();
const kb = document.getElementById("vdbx-search-kb").value.trim();
const topK = Number(document.getElementById("vdbx-search-topk").value || "5");
const thresholdText = document.getElementById("vdbx-search-threshold").value.trim();
const out = document.getElementById("vdbx-search-results");
if (!q) {
    out.textContent = "Enter query first.";
    return;
}
out.textContent = "Searching...";
try {
    const body = { query: q, top_k: topK };
    if (kb) body.knowledge_base_slug = kb;
    if (thresholdText) body.score_threshold = Number(thresholdText);
    const data = await api("/api/v1/vector-db/search-playground/", {
        method: "POST",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify(body),
    });
    const rows = data.results || [];
    if (!rows.length) {
        out.innerHTML = '<span class="vdbx-tip">No chunks retrieved.</span>';
        return;
    }
    out.innerHTML = rows.map((r) =>
        '<div class="vdbx-card" style="margin-top:8px;">' +
            '<h4>Score: ' + Number(r.score || 0).toFixed(4) + ' <span class="vdbx-badge vdbx-gray">' + (r.source || '-') + '</span></h4>' +
            '<div class="body"><div style="white-space:pre-wrap; font-size:12px; color:#29456b;">' + (r.text || '').replace(/</g, '&lt;') + '</div>' +
            '<div class="vdbx-tip" style="margin-top:6px;">Metadata: ' + JSON.stringify(r.metadata || {}) + '</div></div>' +
        '</div>'
    ).join('');
} catch (err) {
    out.innerHTML = '<span class="vdbx-badge vdbx-red">Error</span> ' + err.message;
}
}

async function loadMonitoring() {
const el = document.getElementById("vdbx-monitoring");
try {
    const data = await api("/api/v1/vector-db/system-monitoring/");
    const m = data.monitoring || {};
    const conn = m.qdrant_connectivity || {};
    const usage = m.collection_size_usage || [];
    const growth = m.vector_growth_trend || [];
    const errors = m.error_logs || [];

    const usageHtml = usage.length
        ? '<table class="vdbx-table"><thead><tr><th>Collection</th><th>Points</th><th>Vectors</th></tr></thead><tbody>' +
            usage.map((u) => '<tr><td>' + u.collection + '</td><td>' + u.points_count + '</td><td>' + u.vectors_count + '</td></tr>').join('') +
            '</tbody></table>'
        : '<span class="vdbx-tip">No collection usage data.</span>';

    const growthHtml = growth.length
        ? '<table class="vdbx-table"><thead><tr><th>Date</th><th>New Chunks</th></tr></thead><tbody>' +
            growth.map((g) => '<tr><td>' + g.date + '</td><td>' + g.new_chunks + '</td></tr>').join('') +
            '</tbody></table>'
        : '<span class="vdbx-tip">No growth trend data.</span>';

    const errHtml = errors.length
        ? '<table class="vdbx-table"><thead><tr><th>Action</th><th>Resource</th><th>Time</th></tr></thead><tbody>' +
            errors.map((e) => '<tr><td>' + e.action + '</td><td>' + (e.resource_type || '-') + ':' + (e.resource_id || '-') + '</td><td>' + (e.created_at || '-') + '</td></tr>').join('') +
            '</tbody></table>'
        : '<span class="vdbx-tip">No error logs.</span>';

    el.innerHTML =
        '<div class="vdbx-row2">' +
            '<div class="vdbx-card"><h4>Qdrant Connectivity</h4><div class="body">' +
                '<span class="vdbx-badge ' + badgeClass(conn.connected ? 'connected' : 'disconnected') + '">' + (conn.connected ? 'Connected' : 'Disconnected') + '</span>' +
                '<div class="vdbx-tip" style="margin-top:6px;">Latency: ' + (conn.latency_ms || 0) + 'ms</div>' +
                '<div class="vdbx-tip">Error: ' + (conn.error || 'none') + '</div>' +
            '</div></div>' +
            '<div class="vdbx-card"><h4>Vector Growth Trend</h4><div class="body">' + growthHtml + '</div></div>' +
        '</div>' +
        '<div class="vdbx-card"><h4>Collection Size Usage</h4><div class="body">' + usageHtml + '</div></div>' +
        '<div class="vdbx-card"><h4>Error Logs</h4><div class="body">' + errHtml + '</div></div>';
} catch (err) {
    el.innerHTML = '<span class="vdbx-badge vdbx-red">Error</span> ' + err.message;
}
}

shell.addEventListener("click", async function(evt){
const actionBtn = evt.target.closest("button[data-action]");
if (actionBtn) {
    await collectionAction(actionBtn.getAttribute("data-action"), actionBtn.getAttribute("data-slug"));
    return;
}
const syncBtn = evt.target.closest("button[data-resync]");
if (syncBtn) {
    const id = syncBtn.getAttribute("data-resync");
    try {
        await api("/api/v1/vector-db/sync/" + id + "/resync/", { method: "POST" });
        await loadSync();
    } catch (err) {
        window.alert("Re-sync failed: " + err.message);
    }
    return;
}
const whyBtn = evt.target.closest("button[data-why-toggle]");
if (whyBtn) {
    const panel = document.getElementById("vdbx-why-" + whyBtn.getAttribute("data-why-toggle"));
    if (panel) panel.classList.toggle("open");
    return;
}
const selectBtn = evt.target.closest("button[data-select-provider]");
if (selectBtn) {
    const slug = selectBtn.getAttribute("data-select-provider");
    const embeddingEl = document.getElementById("vdbx-upload-embedding");
    if (embeddingEl) embeddingEl.value = slug;
    highlightSelectedProvider(slug);
    return;
}
const configureBtn = evt.target.closest("button[data-configure-provider]");
if (configureBtn) {
    openProviderConnectionModal(configureBtn.getAttribute("data-configure-provider"));
    return;
}
});

document.getElementById("vdbx-search-run").addEventListener("click", runSearch);
document.getElementById("vdbx-create-collection").addEventListener("click", createCollectionFlow);
document.getElementById("vdbx-collections-refresh").addEventListener("click", loadCollections);
document.getElementById("vdbx-refresh-all").addEventListener("click", async () => {
await Promise.all([loadDashboard(), loadCollections(), loadUploads(), loadSync(), loadEmbedding(), loadMonitoring()]);
});

const compareModal = document.getElementById("vdbx-compare-modal");
document.getElementById("vdbx-compare-providers").addEventListener("click", () => {
document.getElementById("vdbx-compare-body").innerHTML = buildCompareTable();
compareModal.classList.add("open");
});
document.getElementById("vdbx-compare-close").addEventListener("click", () => compareModal.classList.remove("open"));
document.getElementById("vdbx-compare-done").addEventListener("click", () => compareModal.classList.remove("open"));
compareModal.addEventListener("click", (event) => { if (event.target === compareModal) compareModal.classList.remove("open"); });
document.getElementById("vdbx-upload-embedding").addEventListener("change", (event) => {
highlightSelectedProvider(event.target.value);
});

let providerConnSlug = null;
const providerConnModal = document.getElementById("vdbx-provider-conn-modal");

function updateProviderDot(slug, available) {
const dot = document.getElementById("vdbx-dot-" + slug);
if (!dot) return;
dot.classList.toggle("vdbx-dot-green", available);
dot.classList.toggle("vdbx-dot-red", !available);
dot.title = available ? "Available" : "Not configured";
const cached = embeddingProfilesCache.find((p) => p.slug === slug);
if (cached) cached.is_configured = available;
}

function openProviderConnectionModal(slug) {
const profile = embeddingProfilesCache.find((p) => p.slug === slug);
if (!profile) return;
providerConnSlug = slug;
document.getElementById("vdbx-provider-conn-title").textContent = "Configure " + profile.name;
document.getElementById("vdbx-provider-conn-url").value = profile.base_url || "";
document.getElementById("vdbx-provider-conn-key").value = "";
document.getElementById("vdbx-provider-conn-key").placeholder = profile.api_key_set ? "Key is set - leave blank to keep it" : "No key set yet";
document.getElementById("vdbx-provider-conn-proxy").value = profile.proxy_url || "";
document.getElementById("vdbx-provider-conn-timeout").value = profile.connection_timeout_seconds || 10;
document.getElementById("vdbx-provider-conn-status").textContent = "Not tested yet.";
document.getElementById("vdbx-provider-conn-error").textContent = "";
const consoleEl = document.getElementById("vdbx-provider-conn-console");
consoleEl.textContent = 'Click "Console" to run a diagnostic request and see exactly what is sent and received.';
consoleEl.classList.remove("open");
providerConnModal.classList.add("open");
}

async function submitProviderConnection(save) {
if (!providerConnSlug) return;
const button = save ? document.getElementById("vdbx-provider-conn-save") : document.getElementById("vdbx-provider-conn-test");
const originalText = button.textContent;
const errorEl = document.getElementById("vdbx-provider-conn-error");
const statusEl = document.getElementById("vdbx-provider-conn-status");
button.disabled = true;
button.textContent = save ? "Saving..." : "Testing...";
errorEl.textContent = "";
try {
    const body = {
        base_url: document.getElementById("vdbx-provider-conn-url").value.trim(),
        api_key: document.getElementById("vdbx-provider-conn-key").value.trim(),
        proxy_url: document.getElementById("vdbx-provider-conn-proxy").value.trim(),
        connection_timeout_seconds: Number(document.getElementById("vdbx-provider-conn-timeout").value || "10"),
        save: !!save,
    };
    const data = await api("/api/v1/embedding-profiles/" + providerConnSlug + "/connection/", {
        method: "POST",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify(body),
    });
    statusEl.innerHTML = '<span class="vdbx-badge ' + (data.available ? "vdbx-green" : "vdbx-red") + '">' + (data.available ? "Available" : "Unavailable") + '</span> ' +
        '<span class="vdbx-tip">' + (data.detail || "") + (data.latency_ms ? " (" + data.latency_ms + "ms)" : "") + '</span>';
    document.getElementById("vdbx-provider-conn-console").textContent = (data.log && data.log.length) ? data.log.join("\\n") : "No diagnostic output returned.";
    updateProviderDot(providerConnSlug, data.available);
    if (save) {
        if (data.profile) {
            const idx = embeddingProfilesCache.findIndex((p) => p.slug === providerConnSlug);
            if (idx >= 0) embeddingProfilesCache[idx] = data.profile;
        }
        providerConnModal.classList.remove("open");
    }
} catch (err) {
    errorEl.textContent = err.message;
} finally {
    button.disabled = false;
    button.textContent = originalText;
}
}

document.getElementById("vdbx-provider-conn-close").addEventListener("click", () => providerConnModal.classList.remove("open"));
document.getElementById("vdbx-provider-conn-test").addEventListener("click", () => submitProviderConnection(false));
document.getElementById("vdbx-provider-conn-save").addEventListener("click", () => submitProviderConnection(true));
document.getElementById("vdbx-provider-conn-console-btn").addEventListener("click", async () => {
const consoleEl = document.getElementById("vdbx-provider-conn-console");
consoleEl.classList.add("open");
consoleEl.textContent = "Running diagnostic request...";
await submitProviderConnection(false);
});
providerConnModal.addEventListener("click", (event) => { if (event.target === providerConnModal) providerConnModal.classList.remove("open"); });

async function loadKnowledgeBaseOptions() {
try {
    const data = await api("/api/v1/knowledge-bases/");
    const kbs = data.results || [];
    const uploadSelect = document.getElementById("vdbx-upload-kb");
    const connSelect = document.getElementById("vdbx-conn-default-kb");
    const uploadOptions = ['<option value="">Use default collection</option>'].concat(
        kbs.map((kb) => '<option value="' + kb.slug + '">' + kb.name + ' (' + kb.collection + ')</option>')
    ).join('');
    const connOptions = ['<option value="">No default</option>'].concat(
        kbs.map((kb) => '<option value="' + kb.slug + '">' + kb.name + ' (' + kb.collection + ')</option>')
    ).join('');
    if (uploadSelect) uploadSelect.innerHTML = uploadOptions;
    if (connSelect) connSelect.innerHTML = connOptions;
} catch (err) {
    /* Selects fall back to the default-only option if this fails. */
}
}

let embeddingProfilesCache = [];

function costLabel(cost) {
const map = {free: "Free", low: "Low Cost", medium: "Medium Cost", high: "High Cost"};
return map[cost] || cost;
}

function capabilityLabel(capability) {
const map = {online: "Online (Cloud)", offline: "Offline (Local)", hybrid: "Hybrid"};
return map[capability] || capability;
}

function starRating(rating) {
const filled = Math.max(0, Math.min(5, Number(rating) || 0));
return "&#9733;".repeat(filled) + "&#9734;".repeat(5 - filled);
}

function providerCardHtml(profile, isDefault) {
const badgesHtml = (profile.badges || []).map((b) =>
    '<span class="vdbx-provider-badge">' + b.icon + ' ' + b.label + '</span>'
).join('');
const highlightsHtml = (profile.highlights || []).map((h) =>
    '<li>&#10003; ' + h + '</li>'
).join('');
const dotClass = profile.is_configured ? "vdbx-dot-green" : "vdbx-dot-red";
const dotLabel = profile.is_configured ? "Available" : "Not configured";
return (
    '<div class="vdbx-provider-card" data-provider-slug="' + profile.slug + '">' +
        '<div class="vdbx-provider-head">' +
            '<div><div class="vdbx-provider-name">' +
                '<span class="vdbx-status-dot ' + dotClass + '" id="vdbx-dot-' + profile.slug + '" title="' + dotLabel + '"></span>' +
                profile.name + (isDefault ? ' <span class="vdbx-tip">(default)</span>' : '') +
            '</div>' +
            '<div class="vdbx-provider-model">' + (profile.model_name || 'Model not specified') + '</div></div>' +
        '</div>' +
        (badgesHtml ? '<div class="vdbx-provider-badges">' + badgesHtml + '</div>' : '') +
        '<div class="vdbx-provider-meta">' +
            '<div><strong>Dimensions</strong>' + (profile.embedding_dimensions || '-') + '</div>' +
            '<div><strong>Performance</strong><span class="vdbx-stars">' + starRating(profile.performance_rating) + '</span></div>' +
            '<div><strong>Cost</strong>' + costLabel(profile.cost_indicator) + '</div>' +
            '<div><strong>Capability</strong>' + capabilityLabel(profile.capability) + '</div>' +
        '</div>' +
        (highlightsHtml ? '<ul class="vdbx-provider-highlights">' + highlightsHtml + '</ul>' : '') +
        (profile.why_choose ? (
            '<button type="button" class="vdbx-provider-why-toggle" data-why-toggle="' + profile.slug + '">Why choose this provider?</button>' +
            '<div class="vdbx-provider-why" id="vdbx-why-' + profile.slug + '">' + profile.why_choose + '</div>'
        ) : '') +
        '<div class="vdbx-row2" style="margin-top:8px;">' +
            '<button type="button" class="vdbx-btn vdbx-provider-select-btn" data-select-provider="' + profile.slug + '">Use this profile</button>' +
            (profile.provider_type === "default"
                ? ''
                : '<button type="button" class="vdbx-btn" data-configure-provider="' + profile.slug + '">Configure</button>') +
        '</div>' +
    '</div>'
);
}

function highlightSelectedProvider(slug) {
document.querySelectorAll(".vdbx-provider-card").forEach((card) => {
    card.classList.toggle("selected", card.getAttribute("data-provider-slug") === slug);
});
}

async function loadEmbeddingProfiles() {
const cardsEl = document.getElementById("vdbx-provider-cards");
const selectEl = document.getElementById("vdbx-upload-embedding");
try {
    const data = await api("/api/v1/embedding-profiles/");
    embeddingProfilesCache = data.results || [];
    const defaultSlug = data.default_slug || "";

    if (selectEl) {
        selectEl.innerHTML = ['<option value="">Use default embedding</option>'].concat(
            embeddingProfilesCache.map((p) => '<option value="' + p.slug + '">' + p.name + '</option>')
        ).join('');
    }

    if (!embeddingProfilesCache.length) {
        cardsEl.innerHTML = '<span class="vdbx-tip">No embedding profiles configured yet.</span>';
        return;
    }

    cardsEl.innerHTML = embeddingProfilesCache.map((p) => providerCardHtml(p, p.slug === defaultSlug)).join('');
} catch (err) {
    cardsEl.innerHTML = '<span class="vdbx-badge vdbx-red">Error</span> ' + err.message;
}
}

function buildCompareTable() {
if (!embeddingProfilesCache.length) {
    return '<span class="vdbx-tip">No embedding profiles configured yet.</span>';
}
const rows = embeddingProfilesCache.map((p) =>
    '<tr>' +
        '<td><strong>' + p.name + '</strong></td>' +
        '<td>' + (p.model_name || '-') + '</td>' +
        '<td>' + (p.embedding_dimensions || '-') + '</td>' +
        '<td><span class="vdbx-stars">' + starRating(p.performance_rating) + '</span></td>' +
        '<td>' + costLabel(p.cost_indicator) + '</td>' +
        '<td>' + capabilityLabel(p.capability) + '</td>' +
        '<td>' + (p.best_use_case || '-') + '</td>' +
    '</tr>'
).join('');
return '<table class="vdbx-compare-table"><thead><tr>' +
    '<th>Provider</th><th>Model</th><th>Dimensions</th><th>Performance</th><th>Cost</th><th>Capability</th><th>Best Use Case</th>' +
    '</tr></thead><tbody>' + rows + '</tbody></table>';
}

function applyConnectionInfo(data) {
const badge = document.getElementById("vdbx-connection-badge");
const urlSmall = document.getElementById("vdbx-connection-url");
const statusEl = document.getElementById("vdbx-connection-status");
const status = data.connected ? "Connected" : "Disconnected";
if (badge) { badge.textContent = status; badge.className = "vdbx-badge " + badgeClass(status); }
if (urlSmall) urlSmall.textContent = "URL: " + (data.qdrant_url || "not set");
if (statusEl) {
    statusEl.innerHTML = data.connected
        ? '<span class="vdbx-badge vdbx-green">Connected</span> <span class="vdbx-tip">' + (data.collections_found || 0) + ' collection(s) visible from this URL.</span>'
        : '<span class="vdbx-badge vdbx-red">Disconnected</span> <span class="vdbx-tip">' + (data.error || 'Cannot reach Qdrant.') + '</span>';
}
}

async function loadConnection() {
try {
    const data = await api("/api/v1/vector-db/connection/");
    document.getElementById("vdbx-conn-url").value = data.qdrant_url || "";
    document.getElementById("vdbx-conn-timeout").value = data.qdrant_timeout_seconds || 30;
    document.getElementById("vdbx-conn-grpc").checked = !!data.qdrant_prefer_grpc;
    const kbSelect = document.getElementById("vdbx-conn-default-kb");
    if (kbSelect && data.default_knowledge_base_slug) kbSelect.value = data.default_knowledge_base_slug;
    applyConnectionInfo(data);
} catch (err) {
    const statusEl = document.getElementById("vdbx-connection-status");
    if (statusEl) statusEl.innerHTML = '<span class="vdbx-badge vdbx-red">Error</span> ' + err.message;
}
}

async function testOrSaveConnection(persist) {
const button = persist ? document.getElementById("vdbx-conn-save") : document.getElementById("vdbx-conn-test");
const originalText = button.textContent;
button.disabled = true;
button.textContent = persist ? "Saving..." : "Testing...";
try {
    const body = {
        qdrant_url: document.getElementById("vdbx-conn-url").value.trim(),
        qdrant_api_key: document.getElementById("vdbx-conn-key").value.trim(),
        qdrant_prefer_grpc: document.getElementById("vdbx-conn-grpc").checked,
        qdrant_timeout_seconds: Number(document.getElementById("vdbx-conn-timeout").value || "30"),
    };
    if (persist) {
        body.default_knowledge_base_slug = document.getElementById("vdbx-conn-default-kb").value;
    }
    const data = persist
        ? await api("/api/v1/vector-db/connection/", { method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify(body) })
        : await api("/api/v1/vector-db/connection/");
    applyConnectionInfo(data);
    if (persist) {
        document.getElementById("vdbx-conn-key").value = "";
        await loadDashboard();
    }
} catch (err) {
    const statusEl = document.getElementById("vdbx-connection-status");
    if (statusEl) statusEl.innerHTML = '<span class="vdbx-badge vdbx-red">Error</span> ' + err.message;
} finally {
    button.disabled = false;
    button.textContent = originalText;
}
}

document.getElementById("vdbx-conn-test").addEventListener("click", () => testOrSaveConnection(false));
document.getElementById("vdbx-conn-save").addEventListener("click", () => testOrSaveConnection(true));
document.getElementById("vdbx-connection-shortcut").addEventListener("click", () => setActive("connection"));

bindUpload();
loadKnowledgeBaseOptions();
loadEmbeddingProfiles();
loadConnection();
Promise.all([loadDashboard(), loadCollections(), loadUploads(), loadSync(), loadEmbedding(), loadMonitoring()]);
})();
</script>
'''
        return mark_safe(
            html.replace("__CONNECTION_CLASS__", connection_class)
            .replace("__CONNECTION_STATUS__", connection_status)
            .replace("__CONNECTION_DETAIL__", escape(connection_detail))
        )

    class Meta:
        verbose_name = "Qdrant Dashboard"
        verbose_name_plural = "Qdrant Dashboard"
