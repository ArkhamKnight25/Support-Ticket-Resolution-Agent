"""
Phase 4 — Store all processed chunks into ChromaDB.
ChromaDB embeds them locally using all-MiniLM-L6-v2 (no Bedrock quota needed).
Run AFTER ingest_documents.py.
Run: python scripts/embed_and_store.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.config import settings
from app.data_pipeline.ingestion_pipeline import load_all_chunks
from app.vector_store.factory import get_vector_store


def main():
    chunks = load_all_chunks()
    if not chunks:
        print("No chunks found. Run scripts/ingest_documents.py first.")
        return

    print(f"Found {len(chunks)} chunks.")
    print(f"Storing chunks using VECTOR_STORE_TYPE={settings.VECTOR_STORE_TYPE!r}...\n")

    store = get_vector_store(settings)

    existing = store.count()
    if existing > 0:
        print(f"ChromaDB already has {existing} vectors. Resetting and re-storing...")
        store.reset()

    # Batch upsert all chunks at once — fast and no rate limits
    chunk_ids = [c["chunk_id"] for c in chunks]
    texts     = [c["text"] for c in chunks]
    metadatas = [{k: v for k, v in c.items() if k != "text"} for c in chunks]

    store.upsert_batch(chunk_ids, texts, metadatas)

    total = store.count()
    print(f"Done. ChromaDB total vectors: {total}")

    if total == len(chunks):
        print("\nPhase 4 PASSED — all chunks embedded and stored.")
    else:
        print(f"\nWARNING: expected {len(chunks)}, got {total}")


if __name__ == "__main__":
    main()
