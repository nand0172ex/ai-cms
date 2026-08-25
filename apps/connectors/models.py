from django.db import models
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.contrib.settings.models import BaseSiteSetting, register_setting

from apps.core.models import AbstractBaseModel


class ConnectorConfig(AbstractBaseModel):
    class ConnectorType(models.TextChoices):
        JIRA = "jira", "Jira"
        CONFLUENCE = "confluence", "Confluence"

    tenant = models.ForeignKey("tenants.Tenant", null=True, blank=True, on_delete=models.CASCADE)
    knowledge_base = models.ForeignKey("knowledge.KnowledgeBase", on_delete=models.CASCADE, related_name="connectors")
    name = models.CharField(max_length=140)
    connector_type = models.CharField(max_length=20, choices=ConnectorType.choices)
    base_url = models.URLField()
    token_env_var = models.CharField(max_length=120, blank=True)
    access_token = models.CharField(max_length=255, blank=True)
    project_key = models.CharField(max_length=80, blank=True)
    is_active = models.BooleanField(default=True)
    config = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return self.name

    def get_token(self):
        if self.access_token:
            return self.access_token
        if not self.token_env_var:
            return ""
        import os

        return os.getenv(self.token_env_var, "")

    @property
    def masked_token(self):
        token = self.get_token()
        if not token:
            return "(missing)"
        visible = token[-4:] if len(token) >= 4 else token
        return f"{'*' * max(0, len(token) - len(visible))}{visible}"


class ConnectorSyncRun(AbstractBaseModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"

    connector = models.ForeignKey(ConnectorConfig, on_delete=models.CASCADE, related_name="sync_runs")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    fetched_count = models.PositiveIntegerField(default=0)
    indexed_count = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True)


class ConnectorRecord(AbstractBaseModel):
    connector = models.ForeignKey(ConnectorConfig, on_delete=models.CASCADE, related_name="records")
    external_id = models.CharField(max_length=200)
    title = models.CharField(max_length=255)
    content = models.TextField(blank=True)
    source_url = models.URLField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    checksum = models.CharField(max_length=64, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = [("connector", "external_id")]


@register_setting
class ConnectorSettings(BaseSiteSetting):
    """Connector hub settings available under Wagtail Settings menu."""

    jira_base_url = models.URLField(blank=True)
    jira_access_token = models.CharField(max_length=255, blank=True)
    jira_project_key = models.CharField(max_length=80, blank=True)

    confluence_base_url = models.URLField(blank=True)
    confluence_access_token = models.CharField(max_length=255, blank=True)
    confluence_cql = models.CharField(max_length=255, blank=True)

    default_jira_connector = models.ForeignKey(
        ConnectorConfig,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="default_jira_setting",
    )
    default_confluence_connector = models.ForeignKey(
        ConnectorConfig,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="default_confluence_setting",
    )
    auto_sync_enabled = models.BooleanField(default=False)
    sync_interval_minutes = models.PositiveIntegerField(default=60)

    panels = [
        MultiFieldPanel(
            [
                FieldPanel("default_jira_connector"),
                FieldPanel("default_confluence_connector"),
            ],
            heading="Default Connectors",
        ),
        MultiFieldPanel(
            [
                FieldPanel("jira_base_url"),
                FieldPanel("jira_access_token"),
                FieldPanel("jira_project_key"),
                FieldPanel("confluence_base_url"),
                FieldPanel("confluence_access_token"),
                FieldPanel("confluence_cql"),
            ],
            heading="Connection Forms",
        ),
        MultiFieldPanel(
            [
                FieldPanel("auto_sync_enabled"),
                FieldPanel("sync_interval_minutes"),
            ],
            heading="Sync Behavior",
        ),
    ]

    class Meta:
        verbose_name = "Connector Settings"
