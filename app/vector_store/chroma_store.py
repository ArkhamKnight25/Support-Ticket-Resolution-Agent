from pathlib import Path
import chromadb
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

from app.config import Settings
from app.services.logging_service import get_logger

logger = get_logger(__name__)

COLLECTION_NAME = "enterprise-ops"


class ChromaStore:
    """
    ChromaDB vector store.

    Uses ChromaDB's built-in local embedding function (all-MiniLM-L6-v2 via ONNX)
    by default — no Bedrock quota needed. The same function is used for both
    document storage and query embedding, keeping results consistent.

    When Bedrock Titan Embeddings quota becomes available, pre-computed embeddings
    can be passed to upsert() directly and the collection can be recreated with
    embedding_function=None to use raw vectors.
    """

    def __init__(self, settings: Settings) -> None:
        persist_dir = str(settings.CHROMA_PERSIST_DIR)
        Path(persist_dir).mkdir(parents=True, exist_ok=True)

        self._ef = DefaultEmbeddingFunction()
        self._client = chromadb.PersistentClient(path=persist_dir)
        self._collection = self._client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=self._ef,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info("ChromaDB ready", collection=COLLECTION_NAME, path=persist_dir)

    def upsert(self, chunk_id: str, text: str, metadata: dict) -> None:
        """Add or update a chunk. ChromaDB auto-embeds the text."""
        self._collection.upsert(
            ids=[chunk_id],
            documents=[text],
            metadatas=[metadata],
        )

    def upsert_batch(
        self,
        chunk_ids: list[str],
        texts: list[str],
        metadatas: list[dict],
    ) -> None:
        """Batch upsert. ChromaDB auto-embeds all texts."""
        self._collection.upsert(
            ids=chunk_ids,
            documents=texts,
            metadatas=metadatas,
        )
        logger.info("chroma_upsert_batch", count=len(chunk_ids))

    def query(self, query_text: str, top_k: int = 5, where: dict | None = None) -> list[dict]:
        """Query by text. ChromaDB embeds the query using the same local model."""
        n = min(top_k, self._collection.count() or 1)
        kwargs = {
            "query_texts": [query_text],
            "n_results": n,
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            kwargs["where"] = where

        results = self._collection.query(**kwargs)

        docs = []
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            docs.append({"text": doc, "metadata": meta, "score": 1 - dist})
        return docs

    def delete_by_doc_id(self, doc_id: str) -> None:
        results = self._collection.get(where={"doc_id": {"$eq": doc_id}})
        if results["ids"]:
            self._collection.delete(ids=results["ids"])
            logger.info("chroma_delete", doc_id=doc_id, count=len(results["ids"]))

    def count(self) -> int:
        return self._collection.count()

    def reset(self) -> None:
        self._client.delete_collection(COLLECTION_NAME)
        self._collection = self._client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=self._ef,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info("chroma_reset")
