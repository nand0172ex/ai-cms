from apps.knowledge.services.collection_service import CollectionManagementService
from apps.knowledge.services.vectorizer import text_to_vector


class RetrievalService:
    @staticmethod
    def _is_human_readable(text):
        if not text:
            return False
        sample = text[:1200]
        printable = sum(1 for ch in sample if ch.isprintable() or ch in "\n\r\t")
        ratio = printable / max(1, len(sample))
        if ratio < 0.9:
            return False
        if "PK\x03\x04" in text[:120]:
            return False
        return True

    def retrieve(self, retrieval_profile, query, diagnostics=None):
        kb = retrieval_profile.knowledge_base
        collection_name, available, target = self._resolve_live_collection_name(kb)
        if diagnostics is not None:
            diagnostics.update(
                {
                    "kb_slug": getattr(kb, "slug", ""),
                    "target_collection": target,
                    "selected_collection": collection_name,
                    "available_collections": available,
                }
            )
        if not collection_name:
            return []
        return self._retrieve_from_qdrant(
            kb=kb,
            collection_name=collection_name,
            query=query,
            top_k=retrieval_profile.top_k,
            similarity_threshold=retrieval_profile.similarity_threshold,
        )

    def _resolve_live_collection_name(self, kb):
        """Return a Qdrant collection name that currently exists for retrieval.

        Prefer the retrieval profile's configured KB collection; if it no longer
        exists in Qdrant, fall back to another active KB collection that does.
        """
        service = CollectionManagementService(kb)
        try:
            available = sorted(
                {
                item.get("name")
                for item in service.repository.list_collections(include_stats=False)
                if item.get("name")
                }
            )
        except Exception:
            return None, [], kb.effective_collection_name

        target = kb.effective_collection_name
        if target in available:
            return target, available, target

        from apps.knowledge.models import KnowledgeBase

        sibling_kbs = KnowledgeBase.objects.filter(
            is_active=True,
            tenant=kb.tenant,
        ).order_by("id")

        for candidate in sibling_kbs:
            candidate_name = candidate.effective_collection_name
            if candidate_name in available:
                return candidate_name, available, target

        return None, available, target

    def _retrieve_from_qdrant(self, kb, collection_name, query, top_k, similarity_threshold):
        try:
            service = CollectionManagementService(kb)
            query_vector = text_to_vector(query, kb.vector_size)
            hits = service.repository.search_points(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=top_k,
                score_threshold=None,
            )
        except Exception:
            return []

        if not hits:
            return []

        results = []
        for hit in hits:
            payload = getattr(hit, "payload", {}) or {}
            score = float(getattr(hit, "score", 0.0) or 0.0)

            text = payload.get("text")
            chunk_index = payload.get("chunk_index")
            source = payload.get("title") or payload.get("source") or "qdrant"

            if not text:
                continue
            if not self._is_human_readable(text):
                continue

            results.append(
                {
                    "text": text,
                    "score": score,
                    "source": source,
                    "chunk_index": chunk_index,
                }
            )
        return results
