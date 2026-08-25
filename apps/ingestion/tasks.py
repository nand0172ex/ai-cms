import hashlib

from celery import shared_task
from django.utils import timezone

from apps.ingestion.models import IngestedChunk, IngestionJob
from apps.ingestion.services import ChunkingService, DocumentExtractionService
from apps.knowledge.services import CollectionManagementService
from apps.knowledge.services.vectorizer import text_to_vector


@shared_task
def process_ingestion_job(job_id):
    job = IngestionJob.objects.select_related("document", "document__data_source__knowledge_base").get(id=job_id)
    job.status = IngestionJob.Status.RUNNING
    job.started_at = timezone.now()
    job.save(update_fields=["status", "started_at", "updated_at"])

    try:
        extractor = DocumentExtractionService()
        raw_text = extractor.extract_text(job.document)
        chunks = ChunkingService().chunk(raw_text)

        IngestedChunk.objects.filter(document=job.document).delete()
        kb = job.document.data_source.knowledge_base
        collection_service = CollectionManagementService(kb)
        collection_service.create_collection()
        qdrant_points = []
        for idx, text in enumerate(chunks):
            chunk_obj = IngestedChunk.objects.create(
                document=job.document,
                knowledge_base=kb,
                chunk_index=idx,
                text=text,
                metadata={"source": job.document.title},
            )
            point_id = int(hashlib.sha1(f"{job.document.id}:{idx}".encode("utf-8")).hexdigest()[:12], 16)
            qdrant_points.append(
                {
                    "id": point_id,
                    "vector": text_to_vector(text, kb.vector_size),
                    "payload": {
                        "source": "upload",
                        "document_id": job.document.id,
                        "chunk_index": idx,
                        "title": job.document.title,
                        "text": text,
                    },
                }
            )

        if qdrant_points:
            collection_service.repository.upsert_points(kb.effective_collection_name, qdrant_points)

        job.chunk_count = len(chunks)
        job.status = IngestionJob.Status.SUCCESS
        job.finished_at = timezone.now()
        job.document.is_processed = True
        job.document.save(update_fields=["is_processed", "updated_at"])
        job.save(update_fields=["chunk_count", "status", "finished_at", "updated_at"])
    except Exception as exc:
        job.status = IngestionJob.Status.FAILED
        job.error_message = str(exc)
        job.finished_at = timezone.now()
        job.save(update_fields=["status", "error_message", "finished_at", "updated_at"])
        raise
