import json
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from app.config import settings
from app.data_pipeline.document_loader import load_file, load_from_bytes, discover_documents
from app.data_pipeline.chunker import chunk_text
from app.data_pipeline.metadata_extractor import extract_metadata
from app.data_pipeline.quality_checks import filter_chunks
from app.utils.id_utils import generate_doc_id, generate_chunk_id
from app.utils.file_utils import ensure_dir
from app.services.logging_service import get_logger
from app.vector_store.factory import get_vector_store

if TYPE_CHECKING:
    from app.services.embedding_service import EmbeddingService

logger = get_logger(__name__)

PROCESSED_DIR = Path("data/processed/chunks")
METADATA_DIR = Path("data/processed/metadata")
RAW_DIR = Path("data/raw")


def _save_chunk(chunk_data: dict) -> None:
    ensure_dir(PROCESSED_DIR)
    path = PROCESSED_DIR / f"{chunk_data['chunk_id']}.json"
    path.write_text(json.dumps(chunk_data, indent=2), encoding="utf-8")


def _save_doc_metadata(doc_id: str, meta: dict) -> None:
    ensure_dir(METADATA_DIR)
    path = METADATA_DIR / f"{doc_id}.json"
    path.write_text(json.dumps(meta, indent=2), encoding="utf-8")


def ingest_file(file_path: Path) -> tuple[str, int]:
    """
    Ingest a single file: load → chunk → quality filter → save.
    Returns (doc_id, chunk_count).
    """
    doc_id = generate_doc_id(file_path.name)
    raw_text = load_file(file_path)

    if not raw_text.strip():
        logger.warning("Empty document — skipping", file=str(file_path))
        return doc_id, 0

    raw_chunks = chunk_text(raw_text, chunk_size=500, chunk_overlap=50)
    valid_chunks = filter_chunks(raw_chunks)

    saved = 0
    for chunk in valid_chunks:
        chunk_id = generate_chunk_id(doc_id, chunk.chunk_index)
        metadata = extract_metadata(file_path, chunk.chunk_index, chunk_id)
        chunk_data = {"chunk_id": chunk_id, "doc_id": doc_id, "text": chunk.text, **metadata}
        _save_chunk(chunk_data)
        saved += 1

    _save_doc_metadata(doc_id, {
        "doc_id": doc_id,
        "filename": file_path.name,
        "source_path": str(file_path),
        "total_chunks": saved,
        "chunk_count": saved,
        "document_type": valid_chunks and extract_metadata(file_path, 0, "preview").get("document_type") or "unknown",
        "indexed": False,
        "ingested_at": datetime.now(timezone.utc).isoformat(),
    })

    logger.info("Ingested document", file=file_path.name, chunks=saved)
    return doc_id, saved


def ingest_all(raw_dir: Path = RAW_DIR) -> dict:
    """Ingest every document found under raw_dir. Returns summary."""
    files = discover_documents(raw_dir)
    if not files:
        logger.warning("No documents found", dir=str(raw_dir))
        return {"files": 0, "chunks": 0}

    total_files, total_chunks = 0, 0
    for f in files:
        _, count = ingest_file(f)
        total_files += 1
        total_chunks += count

    logger.info("Ingestion complete", files=total_files, chunks=total_chunks)
    return {"files": total_files, "chunks": total_chunks}


def load_all_chunks() -> list[dict]:
    """Load all saved chunks from disk (used by the retriever in Phase 4)."""
    if not PROCESSED_DIR.exists():
        return []
    chunks = []
    for p in PROCESSED_DIR.glob("*.json"):
        try:
            chunks.append(json.loads(p.read_text(encoding="utf-8")))
        except Exception:
            pass
    return chunks


# --- API-facing class (used by document_routes.py) ---

class IngestionPipeline:
    def __init__(self, embedding_service: "EmbeddingService") -> None:
        self.embedding_service = embedding_service
        self._store = get_vector_store(settings)

    async def ingest_bytes(self, content: bytes, filename: str) -> dict:
        doc_id = generate_doc_id(filename)
        raw_text = load_from_bytes(content, filename)

        if not raw_text.strip():
            _save_doc_metadata(doc_id, {
                "doc_id": doc_id,
                "filename": filename,
                "source_path": f"uploads/{filename}",
                "total_chunks": 0,
                "chunk_count": 0,
                "document_type": "unknown",
                "indexed": False,
                "ingested_at": datetime.now(timezone.utc).isoformat(),
            })
            return {
                "document_id": doc_id,
                "filename": filename,
                "document_type": "unknown",
                "chunk_count": 0,
                "indexed": False,
                "status": "failed",
            }

        raw_chunks = chunk_text(raw_text, chunk_size=500, chunk_overlap=50)
        valid_chunks = filter_chunks(raw_chunks)

        # Simulate a source path for metadata extraction
        fake_path = Path(f"data/raw/uploads/{filename}")
        chunk_ids: list[str] = []
        texts: list[str] = []
        metadatas: list[dict] = []

        for chunk in valid_chunks:
            chunk_id = generate_chunk_id(doc_id, chunk.chunk_index)
            metadata = extract_metadata(fake_path, chunk.chunk_index, chunk_id)
            metadata["doc_id"] = doc_id
            chunk_data = {"chunk_id": chunk_id, "doc_id": doc_id, "text": chunk.text, **metadata}
            _save_chunk(chunk_data)
            chunk_ids.append(chunk_id)
            texts.append(chunk.text)
            metadatas.append(metadata)

        if chunk_ids:
            self._store.upsert_batch(chunk_ids, texts, metadatas)

        document_type = metadatas[0].get("document_type", "unknown") if metadatas else "unknown"
        indexed = bool(chunk_ids)

        _save_doc_metadata(doc_id, {
            "doc_id": doc_id,
            "filename": filename,
            "source_path": f"uploads/{filename}",
            "total_chunks": len(valid_chunks),
            "chunk_count": len(valid_chunks),
            "document_type": document_type,
            "indexed": indexed,
            "ingested_at": datetime.now(timezone.utc).isoformat(),
        })
        return {
            "document_id": doc_id,
            "filename": filename,
            "document_type": document_type,
            "chunk_count": len(valid_chunks),
            "indexed": indexed,
            "status": "complete" if indexed else "processing",
        }

    async def list_documents(self) -> list[dict]:
        if not METADATA_DIR.exists():
            return []
        docs = []
        for p in METADATA_DIR.glob("*.json"):
            try:
                raw = json.loads(p.read_text(encoding="utf-8"))
                docs.append(
                    {
                        "document_id": raw.get("doc_id"),
                        "filename": raw.get("filename"),
                        "document_type": raw.get("document_type"),
                        "chunk_count": raw.get("chunk_count", raw.get("total_chunks")),
                        "ingested_at": raw.get("ingested_at"),
                        "indexed": raw.get("indexed", False),
                    }
                )
            except Exception:
                pass
        return docs

    async def delete_document(self, document_id: str) -> bool:
        meta_path = METADATA_DIR / f"{document_id}.json"
        if not meta_path.exists():
            return False
        # Remove all chunks belonging to this doc
        for chunk_file in PROCESSED_DIR.glob(f"{document_id}_chunk_*.json"):
            chunk_file.unlink()
        self._store.delete_by_doc_id(document_id)
        meta_path.unlink()
        return True
