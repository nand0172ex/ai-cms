from collections import defaultdict
from datetime import timedelta
from time import perf_counter

from django.db.models import Count
from django.utils import timezone

from apps.audit.models import AuditEvent
from apps.connectors.models import ConnectorConfig, ConnectorSyncRun
from apps.connectors.services import ConnectorSyncService
from apps.ingestion.models import IngestedChunk, IngestionJob, UploadedDocument
from apps.knowledge.models import KnowledgeBase, QdrantConnection
from apps.knowledge.services.collection_service import CollectionManagementService
from apps.knowledge.services.repository import QdrantRepository
from apps.knowledge.services.vectorizer import text_to_vector


class VectorDBDashboardService:
    """Backend read/write orchestration for enterprise Vector DB dashboard features."""

    def __init__(self, vector_db_settings):
        self.settings = vector_db_settings
        self.repository = QdrantRepository(self._build_runtime_connection())

    def _build_runtime_connection(self):
        return QdrantConnection(
            name="Runtime Vector DB",
            slug="runtime-vector-db",
            url=self.settings.qdrant_url or "http://localhost:6333",
            api_key=self.settings.qdrant_api_key or "",
            # Keep dashboard endpoints on HTTP API to avoid grpc proxy/port issues.
            prefer_grpc=False,
            timeout_seconds=self.settings.qdrant_timeout_seconds or 30,
            is_active=True,
        )

    def _safe_list_collections(self):
        try:
            return self.repository.list_collections(include_stats=True)
        except Exception:
            return []

    def connection_status(self):
        started = perf_counter()
        try:
            self.repository.ping()
            latency_ms = int((perf_counter() - started) * 1000)
            return {"connected": True, "latency_ms": latency_ms, "error": None}
        except Exception as exc:
            latency_ms = int((perf_counter() - started) * 1000)
            return {"connected": False, "latency_ms": latency_ms, "error": str(exc)}

    def dashboard_overview(self):
        connection = self.connection_status()
        collections = []
        total_vectors = 0
        if connection["connected"]:
            collections = self._safe_list_collections()
            total_vectors = sum(item["stats"].get("vectors_count", 0) or 0 for item in collections)

        total_documents = UploadedDocument.objects.count()
        total_chunks = IngestedChunk.objects.count()
        recent_activities = self.recent_activities(limit=12)

        return {
            "total_collections": len(collections),
            "total_vectors": total_vectors,
            "total_documents": total_documents,
            "total_chunks": total_chunks,
            "qdrant_status": "connected" if connection["connected"] else "disconnected",
            "latency_ms": connection["latency_ms"],
            "error": connection["error"],
            "recent_activities": recent_activities,
        }

    def recent_activities(self, limit=20):
        items = []
        for event in AuditEvent.objects.order_by("-created_at")[:limit]:
            items.append(
                {
                    "type": "audit",
                    "label": event.action,
                    "status": "info",
                    "timestamp": event.created_at.isoformat(),
                    "details": {
                        "resource_type": event.resource_type,
                        "resource_id": event.resource_id,
                    },
                }
            )
        for job in IngestionJob.objects.select_related("document").order_by("-created_at")[:limit]:
            items.append(
                {
                    "type": "ingestion",
                    "label": f"Ingestion {job.status}",
                    "status": job.status,
                    "timestamp": job.created_at.isoformat(),
                    "details": {
                        "document": job.document.title,
                        "chunks": job.chunk_count,
                    },
                }
            )
        for run in ConnectorSyncRun.objects.select_related("connector").order_by("-created_at")[:limit]:
            items.append(
                {
                    "type": "sync",
                    "label": f"Connector sync {run.status}",
                    "status": run.status,
                    "timestamp": run.created_at.isoformat(),
                    "details": {
                        "connector": run.connector.name,
                        "indexed_count": run.indexed_count,
                    },
                }
            )
        items.sort(key=lambda x: x["timestamp"], reverse=True)
        return items[:limit]

    def collections_summary(self):
        result = []
        by_effective = {kb.effective_collection_name: kb for kb in KnowledgeBase.objects.select_related("tenant")}
        for item in self._safe_list_collections():
            name = item["name"]
            stats = item["stats"]
            kb = by_effective.get(name)
            health = "green"
            if stats.get("status") not in {"green", "ok", "Healthy", "healthy"}:
                health = "amber"
            if (stats.get("points_count", 0) or 0) == 0:
                health = "amber"

            result.append(
                {
                    "collection": name,
                    "knowledge_base_slug": kb.slug if kb else None,
                    "knowledge_base_name": kb.name if kb else None,
                    "points_count": stats.get("points_count", 0),
                    "vectors_count": stats.get("vectors_count", 0),
                    "vector_size": stats.get("vector_size"),
                    "status": stats.get("status"),
                    "health": health,
                }
            )
        return result

    def create_collection_for_kb(self, kb):
        service = CollectionManagementService(kb)
        created = service.create_collection()
        stats = service.refresh_stats()
        return {"created": created, "stats": stats}

    def delete_collection_for_kb(self, kb):
        service = CollectionManagementService(kb)
        deleted = service.repository.delete_collection(kb.effective_collection_name)
        return {"deleted": deleted, "collection": kb.effective_collection_name}

    def uploads_status(self, limit=50):
        jobs = (
            IngestionJob.objects.select_related("document", "document__data_source", "document__data_source__knowledge_base")
            .order_by("-created_at")[:limit]
        )
        return [
            {
                "job_id": job.id,
                "document": job.document.title,
                "knowledge_base": job.document.data_source.knowledge_base.slug,
                "status": job.status,
                "chunk_count": job.chunk_count,
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "finished_at": job.finished_at.isoformat() if job.finished_at else None,
                "error_message": job.error_message,
            }
            for job in jobs
        ]

    def sync_status(self, limit=50):
        runs = ConnectorSyncRun.objects.select_related("connector").order_by("-created_at")[:limit]
        return [
            {
                "run_id": run.id,
                "connector_id": run.connector_id,
                "connector": run.connector.name,
                "connector_type": run.connector.connector_type,
                "status": run.status,
                "fetched_count": run.fetched_count,
                "indexed_count": run.indexed_count,
                "error_message": run.error_message,
                "created_at": run.created_at.isoformat(),
            }
            for run in runs
        ]

    def connector_summary(self):
        connectors = ConnectorConfig.objects.select_related("knowledge_base").filter(is_active=True).order_by("name")
        latest_runs = {
            item["connector_id"]: item
            for item in ConnectorSyncRun.objects.order_by("connector_id", "-created_at")
            .values("connector_id", "status", "created_at")
        }
        return [
            {
                "connector_id": connector.id,
                "name": connector.name,
                "connector_type": connector.connector_type,
                "knowledge_base": connector.knowledge_base.slug,
                "is_active": connector.is_active,
                "last_sync_status": latest_runs.get(connector.id, {}).get("status"),
                "last_sync_time": latest_runs.get(connector.id, {}).get("created_at"),
            }
            for connector in connectors
        ]

    def trigger_manual_resync(self, connector):
        run = ConnectorSyncService().run_sync(connector)
        return {
            "run_id": run.id,
            "status": run.status,
            "fetched_count": run.fetched_count,
            "indexed_count": run.indexed_count,
        }

    def embedding_monitor(self):
        chunk_counts = IngestedChunk.objects.values("knowledge_base__slug").annotate(total=Count("id"))
        chunks_by_kb = {item["knowledge_base__slug"]: item["total"] for item in chunk_counts}

        success_count = IngestionJob.objects.filter(status=IngestionJob.Status.SUCCESS).count()
        failed_count = IngestionJob.objects.filter(status=IngestionJob.Status.FAILED).count()

        rows = []
        for kb in KnowledgeBase.objects.order_by("name"):
            rows.append(
                {
                    "knowledge_base": kb.slug,
                    "embedding_model": "deterministic-default",
                    "chunk_count": chunks_by_kb.get(kb.slug, 0),
                    "embedding_dimension": kb.vector_size,
                    "processing_status": "active" if kb.is_active else "inactive",
                    "success_count": success_count,
                    "failed_count": failed_count,
                }
            )
        return rows

    def search_playground(self, kb, query, top_k=5, score_threshold=None):
        try:
            query_vector = text_to_vector(query, kb.vector_size)
            service = CollectionManagementService(kb)
            hits = service.repository.search_points(
                collection_name=kb.effective_collection_name,
                query_vector=query_vector,
                limit=top_k,
                score_threshold=score_threshold,
            )
        except Exception:
            return []
        results = []
        for hit in hits:
            payload = getattr(hit, "payload", {}) or {}
            results.append(
                {
                    "score": float(getattr(hit, "score", 0.0) or 0.0),
                    "text": payload.get("text", ""),
                    "source": payload.get("source") or payload.get("title") or "qdrant",
                    "metadata": payload,
                }
            )
        return results

    def system_monitoring(self):
        connection = self.connection_status()
        collections = self._safe_list_collections() if connection["connected"] else []

        usage = []
        for item in collections:
            stats = item["stats"]
            usage.append(
                {
                    "collection": item["name"],
                    "points_count": stats.get("points_count", 0),
                    "vectors_count": stats.get("vectors_count", 0),
                }
            )

        now = timezone.now()
        growth_buckets = defaultdict(int)
        for job in IngestionJob.objects.filter(status=IngestionJob.Status.SUCCESS, created_at__gte=now - timedelta(days=7)):
            key = job.created_at.strftime("%Y-%m-%d")
            growth_buckets[key] += job.chunk_count

        growth = [{"date": key, "new_chunks": growth_buckets[key]} for key in sorted(growth_buckets.keys())]

        errors = list(
            AuditEvent.objects.filter(action__icontains="error")
            .values("id", "action", "resource_type", "resource_id", "created_at")
            .order_by("-created_at")[:50]
        )

        return {
            "qdrant_connectivity": connection,
            "collection_size_usage": usage,
            "vector_growth_trend": growth,
            "error_logs": errors,
        }
