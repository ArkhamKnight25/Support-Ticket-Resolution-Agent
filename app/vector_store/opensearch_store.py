"""
OpenSearch-backed document store using the REST API directly.

This implementation uses text search rather than vector search so the production
profile is no longer a dead end during demos. It keeps the same public
interface as ChromaStore for painless switching via VECTOR_STORE_TYPE.
"""

from __future__ import annotations

import base64
import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from app.config import Settings
from app.services.logging_service import get_logger

logger = get_logger(__name__)


class OpenSearchStore:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.endpoint = (settings.OPENSEARCH_ENDPOINT or "http://localhost:9200").rstrip("/")
        self.index = settings.OPENSEARCH_INDEX
        self._ensure_index()

    def _headers(self, *, content_type: str = "application/json") -> dict[str, str]:
        headers = {"Content-Type": content_type}
        parsed = urlparse(self.endpoint)
        if parsed.username:
            credentials = f"{parsed.username}:{parsed.password or ''}".encode("utf-8")
            headers["Authorization"] = f"Basic {base64.b64encode(credentials).decode('ascii')}"
        return headers

    def _request(
        self,
        method: str,
        path: str,
        payload: str | bytes | None = None,
        *,
        content_type: str = "application/json",
        swallow_404: bool = False,
    ) -> dict | list | None:
        data = payload.encode("utf-8") if isinstance(payload, str) else payload
        req = Request(
            url=f"{self.endpoint}/{path.lstrip('/')}",
            data=data,
            method=method,
            headers=self._headers(content_type=content_type),
        )
        try:
            with urlopen(req, timeout=10) as response:
                body = response.read().decode("utf-8")
                return json.loads(body) if body else None
        except HTTPError as exc:
            if swallow_404 and exc.code == 404:
                return None
            detail = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(
                f"OpenSearch request failed ({exc.code}) for {method} /{path}: {detail[:200]}"
            ) from exc

    def _ensure_index(self) -> None:
        existing = self._request("GET", self.index, swallow_404=True)
        if existing is not None:
            return

        body = json.dumps(
            {
                "settings": {"index": {"number_of_shards": 1, "number_of_replicas": 0}},
                "mappings": {
                    "properties": {
                        "doc_id": {"type": "keyword"},
                        "chunk_id": {"type": "keyword"},
                        "source_file": {"type": "keyword"},
                        "document_type": {"type": "keyword"},
                        "service": {"type": "keyword"},
                        "chunk_index": {"type": "integer"},
                        "text": {"type": "text"},
                        "metadata": {"type": "object", "enabled": True},
                    }
                },
            }
        )
        self._request("PUT", self.index, body)
        logger.info("opensearch_index_created", index=self.index, endpoint=self.endpoint)

    def upsert(self, chunk_id: str, text: str, metadata: dict) -> None:
        self.upsert_batch([chunk_id], [text], [metadata])

    def upsert_batch(
        self,
        chunk_ids: list[str],
        texts: list[str],
        metadatas: list[dict],
    ) -> None:
        lines: list[str] = []
        for chunk_id, text, metadata in zip(chunk_ids, texts, metadatas, strict=False):
            lines.append(json.dumps({"index": {"_index": self.index, "_id": chunk_id}}))
            lines.append(
                json.dumps(
                    {
                        "doc_id": metadata.get("doc_id"),
                        "chunk_id": chunk_id,
                        "source_file": metadata.get("source_file"),
                        "document_type": metadata.get("document_type"),
                        "service": metadata.get("service"),
                        "chunk_index": metadata.get("chunk_index"),
                        "text": text,
                        "metadata": metadata,
                    }
                )
            )
        payload = "\n".join(lines) + "\n"
        self._request("POST", "_bulk", payload, content_type="application/x-ndjson")
        logger.info("opensearch_upsert_batch", count=len(chunk_ids), index=self.index)

    def query(self, query_text: str, top_k: int = 5, where: dict | None = None) -> list[dict]:
        must: list[dict] = [{"multi_match": {"query": query_text, "fields": ["text^2", "source_file"]}}]
        filters: list[dict] = []
        if where:
            for key, value in where.items():
                filters.append({"term": {key: value}})

        body = json.dumps(
            {
                "size": top_k,
                "query": {
                    "bool": {
                        "must": must,
                        "filter": filters,
                    }
                },
            }
        )
        response = self._request("GET", f"{self.index}/_search", body) or {}
        hits = response.get("hits", {}).get("hits", [])
        return [
            {
                "text": hit.get("_source", {}).get("text", ""),
                "metadata": hit.get("_source", {}).get("metadata", {}),
                "score": float(hit.get("_score", 0.0)),
            }
            for hit in hits
        ]

    def delete_by_doc_id(self, doc_id: str) -> None:
        body = json.dumps({"query": {"term": {"doc_id": doc_id}}})
        self._request("POST", f"{self.index}/_delete_by_query", body)
        logger.info("opensearch_delete_by_doc_id", doc_id=doc_id, index=self.index)

    def count(self) -> int:
        response = self._request("GET", f"{self.index}/_count") or {}
        return int(response.get("count", 0))

    def reset(self) -> None:
        self._request("DELETE", self.index, swallow_404=True)
        self._ensure_index()
        logger.info("opensearch_reset", index=self.index)
