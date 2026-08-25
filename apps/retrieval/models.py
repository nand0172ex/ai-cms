from django.db import models

from apps.core.models import AbstractBaseModel


class RetrievalProfile(AbstractBaseModel):
    tenant = models.ForeignKey("tenants.Tenant", null=True, blank=True, on_delete=models.CASCADE)
    name = models.CharField(max_length=120)
    knowledge_base = models.ForeignKey("knowledge.KnowledgeBase", on_delete=models.CASCADE, related_name="retrieval_profiles")
    top_k = models.PositiveIntegerField(default=5)
    similarity_threshold = models.FloatField(default=0.7)
    use_reranking = models.BooleanField(default=False)
    is_default = models.BooleanField(default=False)

    class Meta:
        unique_together = [("tenant", "name")]

    def __str__(self):
        return self.name
