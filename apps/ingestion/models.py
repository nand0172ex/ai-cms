import hashlib

from django.conf import settings
from django.db import models

from apps.core.models import AbstractBaseModel


class DataSource(AbstractBaseModel):
    class SourceType(models.TextChoices):
        UPLOAD = "upload", "Upload"
        CONNECTOR = "connector", "Connector"
        MANUAL = "manual", "Manual"

    tenant = models.ForeignKey("tenants.Tenant", null=True, blank=True, on_delete=models.CASCADE)
    knowledge_base = models.ForeignKey("knowledge.KnowledgeBase", on_delete=models.CASCADE, related_name="data_sources")
    name = models.CharField(max_length=140)
    source_type = models.CharField(max_length=20, choices=SourceType.choices, default=SourceType.UPLOAD)
    is_active = models.BooleanField(default=True)
    config = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return self.name


class UploadedDocument(AbstractBaseModel):
    tenant = models.ForeignKey("tenants.Tenant", null=True, blank=True, on_delete=models.CASCADE)
    data_source = models.ForeignKey(DataSource, on_delete=models.CASCADE, related_name="documents")
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to="ingestion/%Y/%m/%d")
    file_type = models.CharField(max_length=20, blank=True)
    checksum = models.CharField(max_length=64, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)
    is_processed = models.BooleanField(default=False)

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if self.file and not self.file_type:
            self.file_type = self.file.name.split(".")[-1].lower()
        if self.file and not self.checksum:
            hasher = hashlib.sha256()
            for chunk in self.file.chunks():
                hasher.update(chunk)
            self.checksum = hasher.hexdigest()
            self.file.seek(0)
        super().save(*args, **kwargs)


class IngestionJob(AbstractBaseModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"

    document = models.ForeignKey(UploadedDocument, on_delete=models.CASCADE, related_name="jobs")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    chunk_count = models.PositiveIntegerField(default=0)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)


class IngestedChunk(AbstractBaseModel):
    document = models.ForeignKey(UploadedDocument, on_delete=models.CASCADE, related_name="chunks")
    knowledge_base = models.ForeignKey("knowledge.KnowledgeBase", on_delete=models.CASCADE, related_name="chunks")
    chunk_index = models.PositiveIntegerField()
    text = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)
    vector_id = models.CharField(max_length=128, blank=True)

    class Meta:
        unique_together = [("document", "chunk_index")]
