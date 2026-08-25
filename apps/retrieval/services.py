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

    def retrieve(self, retrieval_profile, query):
        kb = retrieval_profile.knowledge_base
        return self._retrieve_from_qdrant(
            kb=kb,
            query=query,
            top_k=retrieval_profile.top_k,
            similarity_threshold=retrieval_profile.similarity_threshold,
        )

    def _retrieve_from_qdrant(self, kb, query, top_k, similarity_threshold):
        try:
            service = CollectionManagementService(kb)
            query_vector = text_to_vector(query, kb.vector_size)
            hits = service.repository.search_points(
                collection_name=kb.effective_collection_name,
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
