from django.db import models

from apps.core.models import AbstractBaseModel


class WorkflowRun(AbstractBaseModel):
    class Status(models.TextChoices):
        STARTED = "started", "Started"
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"

    tenant = models.ForeignKey("tenants.Tenant", null=True, blank=True, on_delete=models.CASCADE)
    prompt_template = models.ForeignKey("prompts.PromptTemplate", null=True, blank=True, on_delete=models.SET_NULL)
    retrieval_profile = models.ForeignKey("retrieval.RetrievalProfile", null=True, blank=True, on_delete=models.SET_NULL)
    query = models.TextField()
    rewritten_query = models.TextField(blank=True)
    response_text = models.TextField(blank=True)
    citations = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.STARTED)
    error_message = models.TextField(blank=True)
