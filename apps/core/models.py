from django.db import models


class AbstractBaseModel(models.Model):
	"""Common timestamp fields used across project models."""

	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		abstract = True
