import os
from urllib.parse import urlparse

from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, PointStruct, VectorParams

from .interfaces import BaseVectorRepository


class QdrantRepository(BaseVectorRepository):
    """Qdrant-backed repository implementation."""

    def __init__(self, connection):
        self.connection = connection
        self.client = None

    def _get_client(self):
        if self.client is not None:
            return self.client

        parsed_url = urlparse(self.connection.url)
        if parsed_url.hostname:
            current_no_proxy = [value.strip() for value in os.environ.get("NO_PROXY", "").split(",") if value.strip()]
            for host in [parsed_url.hostname, "localhost", "127.0.0.1", "0.0.0.0"]:
                if host and host not in current_no_proxy:
                    current_no_proxy.append(host)
            no_proxy_value = ",".join(current_no_proxy)
            os.environ["NO_PROXY"] = no_proxy_value
            os.environ["no_proxy"] = no_proxy_value

        self.client = QdrantClient(
            url=self.connection.url,
            api_key=self.connection.get_api_key() or None,
            prefer_grpc=self.connection.prefer_grpc,
            https=self.connection.url.startswith("https://"),
            timeout=self.connection.timeout_seconds,
            check_compatibility=False,
        )
        return self.client

    def ping(self):
        self._get_client().get_collections()
        return True

    def collection_exists(self, collection_name):
        collections = self._get_client().get_collections().collections
        return any(item.name == collection_name for item in collections)

    def list_collections(self, include_stats=False):
        collections = self._get_client().get_collections().collections
        names = [item.name for item in collections]
        if not include_stats:
            return [{"name": name} for name in names]

        result = []
        for name in names:
            try:
                stats = self.get_collection_stats(name)
            except Exception:
                stats = {
                    "collection_name": name,
                    "status": "unknown",
                    "points_count": 0,
                    "vectors_count": 0,
                    "vector_size": None,
                }
            result.append({"name": name, "stats": stats})
        return result

    def create_collection(self, collection_name, vector_size):
        if self.collection_exists(collection_name):
            return False

        self._get_client().create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )
        return True

    def delete_collection(self, collection_name):
        if not self.collection_exists(collection_name):
            return False
        self._get_client().delete_collection(collection_name=collection_name)
        return True

    def get_collection_stats(self, collection_name):
        info = self._get_client().get_collection(collection_name)
        points_count = getattr(info, "points_count", 0)
        vectors_count = getattr(info, "vectors_count", points_count)

        config = getattr(info, "config", None)
        params = getattr(config, "params", None)
        vectors_cfg = getattr(params, "vectors", None)
        vector_size = getattr(vectors_cfg, "size", None)

        return {
            "collection_name": collection_name,
            "status": str(getattr(info, "status", "unknown")),
            "points_count": points_count,
            "vectors_count": vectors_count,
            "vector_size": vector_size,
        }

    def upsert_points(self, collection_name, points):
        payload = [
            PointStruct(id=item["id"], vector=item["vector"], payload=item.get("payload", {}))
            for item in points
        ]
        self._get_client().upsert(collection_name=collection_name, points=payload)
        return len(payload)

    def search_points(self, collection_name, query_vector, limit=5, score_threshold=None):
        client = self._get_client()

        if hasattr(client, "query_points"):
            result = client.query_points(
                collection_name=collection_name,
                query=query_vector,
                limit=limit,
                score_threshold=score_threshold,
            )
            points = getattr(result, "points", result)
            return list(points)

        return client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=limit,
            score_threshold=score_threshold,
        )
