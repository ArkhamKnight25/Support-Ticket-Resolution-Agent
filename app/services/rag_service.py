from app.config import Settings
from app.services.embedding_service import EmbeddingService
from app.vector_store.retriever import Retriever, RetrievedDocument
from app.services.logging_service import get_logger

logger = get_logger(__name__)


class RAGService:
    def __init__(self, settings: Settings, embedding_service: EmbeddingService) -> None:
        self.settings = settings
        self._retriever = Retriever(settings)

    async def retrieve(self, query: str, top_k: int = 5) -> list[RetrievedDocument]:
        return await self._retriever.retrieve(query, top_k=top_k)
