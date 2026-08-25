from django.db import models

from apps.core.models import AbstractBaseModel


class HealthSnapshot(AbstractBaseModel):
    component = models.CharField(max_length=120)
    status = models.CharField(max_length=30)
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
