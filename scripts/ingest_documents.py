"""
Phase 3 — Ingest all documents from data/raw/ into data/processed/
Run: python scripts/ingest_documents.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from pathlib import Path
from app.data_pipeline.ingestion_pipeline import ingest_all, load_all_chunks

RAW_DIR = Path("data/raw")


def main():
    print(f"Scanning {RAW_DIR} for documents...")
    result = ingest_all(RAW_DIR)

    print(f"\nIngestion complete:")
    print(f"  Files processed : {result['files']}")
    print(f"  Chunks saved    : {result['chunks']}")

    chunks = load_all_chunks()
    print(f"\nSample chunk (first one):")
    if chunks:
        c = chunks[0]
        print(f"  chunk_id      : {c['chunk_id']}")
        print(f"  source_file   : {c['source_file']}")
        print(f"  document_type : {c['document_type']}")
        print(f"  service       : {c['service']}")
        print(f"  text preview  : {c['text'][:120]}...")
    else:
        print("  No chunks found.")


if __name__ == "__main__":
    main()
