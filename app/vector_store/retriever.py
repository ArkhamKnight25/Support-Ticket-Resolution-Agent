from dataclasses import dataclass
from app.config import Settings
from app.vector_store.factory import get_vector_store
from app.services.logging_service import get_logger

logger = get_logger(__name__)


@dataclass
class RetrievedDocument:
    page_content: str
    metadata: dict
    score: float = 0.0


class Retriever:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._store = get_vector_store(settings)

    async def retrieve(self, query: str, top_k: int = 5) -> list[RetrievedDocument]:
        if self._store.count() == 0:
            logger.warning("Vector store is empty — run embed_and_store.py first")
            return []

        raw_results = self._store.query(query, top_k=top_k)

        docs = [
            RetrievedDocument(
                page_content=r["text"],
                metadata=r["metadata"],
                score=r["score"],
            )
            for r in raw_results
        ]

        logger.info("retrieval_complete", query_preview=query[:60], results=len(docs))
        return docs
