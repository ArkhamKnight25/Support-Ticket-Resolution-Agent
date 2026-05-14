from app.config import Settings
from app.vector_store.chroma_store import ChromaStore
from app.vector_store.opensearch_store import OpenSearchStore


def get_vector_store(settings: Settings):
    if settings.VECTOR_STORE_TYPE.lower() == "opensearch":
        return OpenSearchStore(settings)
    return ChromaStore(settings)

