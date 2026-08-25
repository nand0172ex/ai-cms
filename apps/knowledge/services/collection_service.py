from django.conf import settings

from apps.knowledge.models import QdrantConnection

from .repository import QdrantRepository


class CollectionManagementService:
    """Service layer for knowledge-base collection lifecycle."""

    def __init__(self, knowledge_base):
        self.knowledge_base = knowledge_base
        self.connection = self._resolve_connection()
        self.repository = QdrantRepository(self.connection)

    def _resolve_connection(self):
        if self.knowledge_base.qdrant_connection_id:
            return self.knowledge_base.qdrant_connection

        scope_filter = {"tenant": self.knowledge_base.tenant} if self.knowledge_base.tenant_id else {"tenant__isnull": True}
        connection = QdrantConnection.objects.filter(
            is_active=True,
            is_default=True,
            **scope_filter,
        ).first()

        if connection:
            return connection

        fallback = QdrantConnection.objects.filter(
            tenant__isnull=True,
            is_active=True,
            is_default=True,
        ).first()
        if fallback:
            return fallback

        return QdrantConnection(
            name="Ephemeral Local Qdrant",
            slug="ephemeral-local-qdrant",
            url=settings.QDRANT_URL,
            api_key_env_var="QDRANT_API_KEY",
            is_active=True,
            is_default=True,
        )

    def test_connection(self):
        return self.repository.ping()

    def create_collection(self):
        return self.repository.create_collection(
            collection_name=self.knowledge_base.effective_collection_name,
            vector_size=self.knowledge_base.vector_size,
        )

    def validate_collection(self):
        return self.repository.collection_exists(self.knowledge_base.effective_collection_name)

    def refresh_stats(self):
        stats = self.repository.get_collection_stats(self.knowledge_base.effective_collection_name)
        self.knowledge_base.document_count = stats.get("points_count") or 0
        self.knowledge_base.save(update_fields=["document_count", "updated_at"])
        return stats
