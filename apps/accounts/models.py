import base64
import hashlib

from cryptography.fernet import Fernet
from django.conf import settings
from django.db import models


class AbstractBaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UserEmbeddingCredential(AbstractBaseModel):
    """Encrypted embedding-provider credential owned by exactly one user."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="embedding_credentials")
    embedding_profile = models.ForeignKey(
        "knowledge.EmbeddingProfile", on_delete=models.CASCADE, related_name="user_credentials"
    )
    encrypted_api_key = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "embedding_profile"], name="unique_user_embedding_credential"
            )
        ]

    def _cipher(self):
        key = hashlib.sha256(settings.FIELD_ENCRYPTION_KEY.encode("utf-8")).digest()
        return Fernet(base64.urlsafe_b64encode(key))

    def set_api_key(self, value):
        self.encrypted_api_key = self._cipher().encrypt((value or "").encode("utf-8")).decode("ascii")

    def get_api_key(self):
        if not self.encrypted_api_key:
            return ""
        return self._cipher().decrypt(self.encrypted_api_key.encode("ascii")).decode("utf-8")

    @property
    def masked_api_key(self):
        value = self.get_api_key()
        return f"Bearer ****{value[-4:]}" if value else ""
