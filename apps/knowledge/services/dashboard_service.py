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
    def embedding_monitor(self, user=None):
        jobs = IngestionJob.objects.select_related(
            "document", "document__data_source", "document__data_source__knowledge_base"
        )
        if user is not None and not getattr(user, "is_superuser", False):
            jobs = jobs.filter(created_by=user)
        jobs = list(jobs.order_by("-created_at"))
        if not jobs:
            return []

        connection = self.connection_status()
        rows = []
        seen_kbs = set()
        for job in jobs:
            kb = job.document.data_source.knowledge_base
            if kb.pk in seen_kbs:
                continue
            seen_kbs.add(kb.pk)
            collection_exists = None
            collection_points = 0
            if connection["connected"]:
                try:
                    collection_exists = self.repository.collection_exists(kb.effective_collection_name)
                    if collection_exists:
                        collection_points = self.repository.get_collection_stats(
                            kb.effective_collection_name
                        ).get("points_count", 0) or 0
                except Exception:
                    collection_exists = False

            if not connection["connected"]:
                processing_status = "qdrant_unavailable"
                status_detail = connection["error"] or "Configured Qdrant host is unavailable."
            elif not collection_exists:
                processing_status = "collection_missing"
                status_detail = "No matching collection exists on the configured Qdrant host."
            elif job.status == IngestionJob.Status.PENDING:
                processing_status = "queued"
                status_detail = "Document is queued for ingestion."
            elif job.status == IngestionJob.Status.RUNNING:
                processing_status = "processing"
                status_detail = "Document ingestion is currently running."
            elif job.status == IngestionJob.Status.FAILED:
                processing_status = "failed"
                status_detail = job.error_message or "Document ingestion failed."
            else:
                processing_status = "complete"
                status_detail = "Document ingestion is complete."

            rows.append(
                {
                    "knowledge_base": kb.slug,
                    "embedding_model": "deterministic-default",
                    "chunk_count": job.chunk_count,
                    "qdrant_points": collection_points,
                    "embedding_dimension": kb.vector_size,
                    "processing_status": processing_status,
                    "status_detail": status_detail,
                    "qdrant_status": "connected" if connection["connected"] else "unavailable",
                    "collection_status": "available" if collection_exists else "missing" if collection_exists is False else "unknown",
                    "success_count": sum(
                        item.status == IngestionJob.Status.SUCCESS
                        and item.document.data_source.knowledge_base_id == kb.pk
                        for item in jobs
                    ),
                    "failed_count": sum(
                        item.status == IngestionJob.Status.FAILED
                        and item.document.data_source.knowledge_base_id == kb.pk
                        for item in jobs
                    ),
                }
            )
        return rows

    def create_collection_for_kb(self, kb):
        service = CollectionManagementService(kb)
        created = service.create_collection()
        stats = service.refresh_stats()
        return {"created": created, "stats": stats}

    def delete_collection_for_kb(self, kb):
        service = CollectionManagementService(kb)
        deleted = service.repository.delete_collection(kb.effective_collection_name)
        return {"deleted": deleted, "collection": kb.effective_collection_name}

    def uploads_status(self, limit=50, user=None):
        connection = self.connection_status()
        jobs_query = IngestionJob.objects.select_related(
            "document", "document__data_source", "document__data_source__knowledge_base"
        )
        if user is not None and not getattr(user, "is_superuser", False):
            jobs_query = jobs_query.filter(created_by=user)
        jobs = jobs_query.order_by("-created_at")[:limit]
        rows = []
        for job in jobs:
            kb = job.document.data_source.knowledge_base
            collection_exists = None
            if connection["connected"]:
                try:
                    collection_exists = self.repository.collection_exists(kb.effective_collection_name)
                except Exception:
                    collection_exists = False

            if not connection["connected"]:
                status_detail = "Qdrant unavailable; ingestion status is from the local job record."
            elif collection_exists is False:
                status_detail = "Collection is missing on the configured Qdrant host."
            elif job.status == IngestionJob.Status.SUCCESS:
                status_detail = "Ingestion completed and the collection is available."
            else:
                status_detail = f"Local ingestion job is {job.status}."

            rows.append(
                {
                    "job_id": job.id,
                    "document": job.document.title,
                    "knowledge_base": kb.slug,
                    "collection": kb.effective_collection_name,
                    "status": job.status,
                    "chunk_count": job.chunk_count,
                    "started_at": job.started_at.isoformat() if job.started_at else None,
                    "finished_at": job.finished_at.isoformat() if job.finished_at else None,
                    "error_message": job.error_message,
                    "qdrant_status": "connected" if connection["connected"] else "unavailable",
                    "collection_status": (
                        "available" if collection_exists else "missing" if collection_exists is False else "unknown"
                    ),
                    "status_detail": status_detail,
                }
            )
        return {
            "qdrant": {
                "status": "connected" if connection["connected"] else "unavailable",
                "url": self.settings.qdrant_url or "http://localhost:6333",
                "latency_ms": connection["latency_ms"],
                "error": connection["error"],
            },
            "results": rows,
        }

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
