from django.conf import settings
from django.db import models
from django.utils.text import slugify

from apps.core.models import AbstractBaseModel


class PromptTemplate(AbstractBaseModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        APPROVED = "approved", "Approved"
        ARCHIVED = "archived", "Archived"

    tenant = models.ForeignKey(
        "tenants.Tenant",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="prompt_templates",
    )
    key = models.CharField(max_length=120, help_text="Stable logical key for prompt family")
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=170)
    version = models.PositiveIntegerField(default=1)
    description = models.TextField(blank=True)
    template = models.TextField()
    variables = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="approved_prompts",
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["key", "-version"]
        unique_together = [("tenant", "key", "version"), ("tenant", "slug")]

    def __str__(self):
        return f"{self.key} v{self.version}"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(f"{self.key}-v{self.version}")
        super().save(*args, **kwargs)

    def render(self, context):
        rendered = self.template
        for key, value in context.items():
            rendered = rendered.replace("{{ " + key + " }}", str(value))
            rendered = rendered.replace("{{" + key + "}}", str(value))
        return rendered
