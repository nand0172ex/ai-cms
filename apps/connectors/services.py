import hashlib
from datetime import datetime
from datetime import timedelta
from urllib.parse import urljoin

import requests

from apps.connectors.models import ConnectorRecord, ConnectorSyncRun
from apps.knowledge.services import CollectionManagementService
from apps.knowledge.services.vectorizer import text_to_vector


class BaseConnectorClient:
    def __init__(self, config):
        self.config = config
        self.token = config.get_token()

    def headers(self):
        auth_type = str(self.config.config.get("auth_type", "bearer") or "bearer").lower()
        headers = dict(self.config.config.get("headers") or {})

        if auth_type == "none":
            return headers

        if auth_type == "api_key":
            header_name = (self.config.config.get("api_key_header") or "X-API-Key").strip()
            key_val = (self.config.config.get("api_key") or self.token or "").strip()
            if header_name and key_val:
                headers[header_name] = key_val
            return headers

        if auth_type == "basic":
            username = (self.config.config.get("username") or "").strip()
            password = (self.config.config.get("password") or self.token or "").strip()
            if username and password:
                import base64

                raw = f"{username}:{password}".encode("utf-8")
                headers["Authorization"] = f"Basic {base64.b64encode(raw).decode('utf-8')}"
            return headers

        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _timeout(self):
        try:
            return int(self.config.config.get("timeout_seconds") or 30)
        except Exception:
            return 30

    def _proxies(self):
        proxy_url = (self.config.config.get("proxy_url") or "").strip()
        if not proxy_url:
            return None
        return {
            "http": proxy_url,
            "https": proxy_url,
        }

    def _request(self, method, url, **kwargs):
        if "proxies" not in kwargs:
            proxies = self._proxies()
            if proxies:
                kwargs["proxies"] = proxies
        response = requests.request(
            method=method,
            url=url,
            headers=self.headers(),
            timeout=self._timeout(),
            **kwargs,
        )
        response.raise_for_status()
        return response

    def _extract_path(self, payload, path, default=None):
        if not path:
            return payload
        node = payload
        for part in str(path).split("."):
            if isinstance(node, list):
                try:
                    node = node[int(part)]
                except Exception:
                    return default
            elif isinstance(node, dict):
                node = node.get(part)
            else:
                return default
            if node is None:
                return default
        return node

    def _as_text(self, value):
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        return str(value)

    def _normalize_item(self, item, mapping):
        ext_id = self._as_text(self._extract_path(item, mapping.get("id", "id"), default="")).strip()
        title = self._as_text(
            self._extract_path(item, mapping.get("title", "title"), default="Untitled")
        ).strip() or "Untitled"

        content_paths = mapping.get("content_paths") or []
        if content_paths:
            content = "\n\n".join(
                [self._as_text(self._extract_path(item, p, default="")).strip() for p in content_paths]
            ).strip()
        else:
            content = self._as_text(self._extract_path(item, mapping.get("content", "content"), default="")).strip()

        source_url = self._as_text(self._extract_path(item, mapping.get("url", "url"), default="")).strip()
        if source_url and not source_url.startswith("http"):
            source_url = urljoin(self.config.base_url.rstrip("/") + "/", source_url.lstrip("/"))

        metadata = {
            "connector_type": self.config.connector_type,
            "source_name": self.config.name,
        }
        metadata_fields = mapping.get("metadata_fields") or []
        for field in metadata_fields:
            metadata[field] = self._extract_path(item, field)

        incremental_field = mapping.get("incremental_field") or "updated_at"
        metadata["incremental_value"] = self._extract_path(item, incremental_field)

        return {
            "id": ext_id,
            "title": title,
            "content": content,
            "url": source_url,
            "metadata": metadata,
        }

    def test_connection(self):
        self._request("GET", self.config.base_url)
        return True

    def fetch_items(self):
        return []


class JiraConnectorClient(BaseConnectorClient):
    def fetch_items(self):
        jql = self.config.config.get("jql", "ORDER BY updated DESC")
        last_cursor = (self.config.config.get("last_cursor") or "").strip()
        if (self.config.config.get("sync_mode") or "incremental") == "incremental" and last_cursor:
            jql = f"updated >= '{last_cursor}' AND ({jql})"
        url = f"{self.config.base_url.rstrip('/')}/rest/api/3/search"
        response = self._request("GET", url, params={"jql": jql, "maxResults": 20})
        issues = response.json().get("issues", [])
        return [
            {
                "id": issue.get("id", ""),
                "title": issue.get("fields", {}).get("summary", "Untitled"),
                "content": issue.get("fields", {}).get("description", ""),
                "url": f"{self.config.base_url.rstrip('/')}/browse/{issue.get('key','')}",
                "metadata": {
                    "key": issue.get("key"),
                    "incremental_value": issue.get("fields", {}).get("updated"),
                },
            }
            for issue in issues
        ]


class ConfluenceConnectorClient(BaseConnectorClient):
    def fetch_items(self):
        cql = self.config.config.get("cql", "type=page order by lastmodified desc")
        last_cursor = (self.config.config.get("last_cursor") or "").strip()
        if (self.config.config.get("sync_mode") or "incremental") == "incremental" and last_cursor:
            cql = f"lastmodified >= '{last_cursor}' and ({cql})"
        url = f"{self.config.base_url.rstrip('/')}/wiki/rest/api/content/search"
        response = self._request("GET", url, params={"cql": cql, "limit": 20})
        results = response.json().get("results", [])
        return [
            {
                "id": item.get("id", ""),
                "title": item.get("title", "Untitled"),
                "content": "",
                "url": f"{self.config.base_url.rstrip('/')}/wiki{item.get('_links', {}).get('webui', '')}",
                "metadata": {
                    "type": item.get("type"),
                    "incremental_value": item.get("version", {}).get("when"),
                },
            }
            for item in results
        ]


class RestAPIConnectorClient(BaseConnectorClient):
    def fetch_items(self):
        cfg = self.config.config or {}
        endpoint_path = (cfg.get("endpoint_path") or "/").strip()
        method = str(cfg.get("method") or "GET").upper()
        url = urljoin(self.config.base_url.rstrip("/") + "/", endpoint_path.lstrip("/"))

        params = dict(cfg.get("query_params") or {})
        last_cursor = (cfg.get("last_cursor") or "").strip()
        if str(cfg.get("sync_mode") or "incremental").lower() == "incremental" and last_cursor:
            incremental_param = (cfg.get("incremental_param") or "updated_since").strip()
            if incremental_param:
                params[incremental_param] = last_cursor

        response = self._request(method, url, params=params)
        payload = response.json() if response.text else {}
        items_path = cfg.get("items_path") or "results"
        items = self._extract_path(payload, items_path, default=[])
        if isinstance(items, dict):
            items = [items]
        if not isinstance(items, list):
            return []

        mapping = {
            "id": cfg.get("id_field") or "id",
            "title": cfg.get("title_field") or "title",
            "content": cfg.get("content_field") or "content",
            "content_paths": cfg.get("content_paths") or [],
            "url": cfg.get("url_field") or "url",
            "metadata_fields": cfg.get("metadata_fields") or [],
            "incremental_field": cfg.get("incremental_field") or "updated_at",
        }
        normalized = []
        for raw in items:
            item = self._normalize_item(raw, mapping)
            if item.get("id"):
                normalized.append(item)
        return normalized


class ConnectorRegistry:
    TYPES = {
        "jira": JiraConnectorClient,
        "confluence": ConfluenceConnectorClient,
        "rest_api": RestAPIConnectorClient,
    }

    @classmethod
    def get_client(cls, config):
        client_cls = cls.TYPES.get(config.connector_type, RestAPIConnectorClient)
        return client_cls(config)


class ConnectorSyncService:
    def _interval_minutes(self, connector_config):
        try:
            interval = int((connector_config.config or {}).get("sync_interval_minutes") or 30)
        except Exception:
            interval = 30
        return 1440 if interval >= 1440 else 30

    def _is_due(self, connector_config):
        interval = self._interval_minutes(connector_config)
        last_success = (
            ConnectorSyncRun.objects.filter(
                connector=connector_config,
                status=ConnectorSyncRun.Status.SUCCESS,
            )
            .order_by("-created_at")
            .first()
        )
        if not last_success:
            return True
        return datetime.utcnow() >= (last_success.created_at.replace(tzinfo=None) + timedelta(minutes=interval))

    def run_sync(self, connector_config, force=True):
        if not force and not self._is_due(connector_config):
            return ConnectorSyncRun.objects.create(
                connector=connector_config,
                status=ConnectorSyncRun.Status.SUCCESS,
                fetched_count=0,
                indexed_count=0,
                error_message="Skipped (not due yet for configured schedule).",
            )

        run = ConnectorSyncRun.objects.create(connector=connector_config, status=ConnectorSyncRun.Status.RUNNING)
        try:
            client = ConnectorRegistry.get_client(connector_config)
            items = client.fetch_items()
            run.fetched_count = len(items)
            indexed = 0
            max_cursor = None
            seen_external_ids = set()
            for item in items:
                payload = (item.get("title", "") + "\n" + item.get("content", "")).encode("utf-8")
                checksum = hashlib.sha256(payload).hexdigest()
                seen_external_ids.add(item["id"])
                previous = ConnectorRecord.objects.filter(
                    connector=connector_config,
                    external_id=item["id"],
                ).only("checksum").first()
                record, created = ConnectorRecord.objects.update_or_create(
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
                if created or (previous and previous.checksum != checksum):
                    indexed += 1

                cursor_val = (item.get("metadata") or {}).get("incremental_value")
                if cursor_val:
                    as_text = str(cursor_val)
                    if max_cursor is None or as_text > max_cursor:
                        max_cursor = as_text

            if bool((connector_config.config or {}).get("deactivate_missing", False)) and seen_external_ids:
                ConnectorRecord.objects.filter(connector=connector_config).exclude(
                    external_id__in=seen_external_ids
                ).update(is_active=False)

            self._index_records_in_qdrant(connector_config)

            cfg = dict(connector_config.config or {})
            cfg["last_sync_at"] = datetime.utcnow().isoformat() + "Z"
            if max_cursor:
                cfg["last_cursor"] = max_cursor
            connector_config.config = cfg
            connector_config.save(update_fields=["config", "updated_at"])

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
                        "source_name": connector_config.name,
                        "connector_id": connector_config.id,
                        "connector_type": connector_config.connector_type,
                        "embedding_profile_slug": (connector_config.config or {}).get("embedding_profile_slug", ""),
                        "external_id": record.external_id,
                        "title": record.title,
                        "url": record.source_url,
                        "text": text,
                        "metadata": record.metadata or {},
                    },
                }
            )

        if points:
            service.repository.upsert_points(kb.effective_collection_name, points)
