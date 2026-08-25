import hashlib

import requests

from apps.connectors.models import ConnectorRecord, ConnectorSyncRun
from apps.knowledge.services import CollectionManagementService
from apps.knowledge.services.vectorizer import text_to_vector


class BaseConnectorClient:
    def __init__(self, config):
        self.config = config
        self.token = config.get_token()

    def headers(self):
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    def test_connection(self):
        response = requests.get(self.config.base_url, headers=self.headers(), timeout=15)
        response.raise_for_status()
        return True

    def fetch_items(self):
        return []


class JiraConnectorClient(BaseConnectorClient):
    def fetch_items(self):
        jql = self.config.config.get("jql", "ORDER BY updated DESC")
        url = f"{self.config.base_url.rstrip('/')}/rest/api/3/search"
        response = requests.get(url, headers=self.headers(), params={"jql": jql, "maxResults": 20}, timeout=30)
        response.raise_for_status()
        issues = response.json().get("issues", [])
        return [
            {
                "id": issue.get("id", ""),
                "title": issue.get("fields", {}).get("summary", "Untitled"),
                "content": issue.get("fields", {}).get("description", ""),
                "url": f"{self.config.base_url.rstrip('/')}/browse/{issue.get('key','')}",
                "metadata": {"key": issue.get("key")},
            }
            for issue in issues
        ]


class ConfluenceConnectorClient(BaseConnectorClient):
    def fetch_items(self):
        cql = self.config.config.get("cql", "type=page order by lastmodified desc")
        url = f"{self.config.base_url.rstrip('/')}/wiki/rest/api/content/search"
        response = requests.get(url, headers=self.headers(), params={"cql": cql, "limit": 20}, timeout=30)
        response.raise_for_status()
        results = response.json().get("results", [])
        return [
            {
                "id": item.get("id", ""),
                "title": item.get("title", "Untitled"),
                "content": "",
                "url": f"{self.config.base_url.rstrip('/')}/wiki{item.get('_links', {}).get('webui', '')}",
                "metadata": {"type": item.get("type")},
            }
            for item in results
        ]


class ConnectorRegistry:
    TYPES = {
        "jira": JiraConnectorClient,
        "confluence": ConfluenceConnectorClient,
    }

    @classmethod
    def get_client(cls, config):
        return cls.TYPES[config.connector_type](config)


class ConnectorSyncService:
    def run_sync(self, connector_config):
        run = ConnectorSyncRun.objects.create(connector=connector_config, status=ConnectorSyncRun.Status.RUNNING)
        try:
            client = ConnectorRegistry.get_client(connector_config)
            items = client.fetch_items()
            run.fetched_count = len(items)
            indexed = 0
            for item in items:
                payload = (item.get("title", "") + "\n" + item.get("content", "")).encode("utf-8")
                checksum = hashlib.sha256(payload).hexdigest()
                ConnectorRecord.objects.update_or_create(
                    connector=connector_config,
                    external_id=item["id"],
                    defaults={
                        "title": item.get("title", "Untitled"),
                        "content": item.get("content", ""),
                        "source_url": item.get("url", ""),
                        "metadata": item.get("metadata", {}),
                        "checksum": checksum,
                        "is_active": True,
                    },
                )
                indexed += 1

            self._index_records_in_qdrant(connector_config)

            run.indexed_count = indexed
            run.status = ConnectorSyncRun.Status.SUCCESS
            run.save(update_fields=["fetched_count", "indexed_count", "status", "updated_at"])
            return run
        except Exception as exc:
            run.status = ConnectorSyncRun.Status.FAILED
            run.error_message = str(exc)
            run.save(update_fields=["status", "error_message", "updated_at"])
            raise

    def _index_records_in_qdrant(self, connector_config):
        kb = connector_config.knowledge_base
        service = CollectionManagementService(kb)
        service.create_collection()

        records = ConnectorRecord.objects.filter(connector=connector_config, is_active=True)
        points = []
        for record in records:
            point_id = int(hashlib.sha1(f"{connector_config.id}:{record.external_id}".encode("utf-8")).hexdigest()[:12], 16)
            text = (record.title or "") + "\n" + (record.content or "")
            vector = text_to_vector(text, kb.vector_size)
            points.append(
                {
                    "id": point_id,
                    "vector": vector,
                    "payload": {
                        "source": "connector",
                        "connector_type": connector_config.connector_type,
                        "external_id": record.external_id,
                        "title": record.title,
                        "url": record.source_url,
                    },
                }
            )

        if points:
            service.repository.upsert_points(kb.effective_collection_name, points)
