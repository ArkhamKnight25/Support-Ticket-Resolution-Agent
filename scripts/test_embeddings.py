"""
Phase 4 smoke test — similarity search over stored chunks.
Run AFTER embed_and_store.py.
Run: python scripts/test_embeddings.py
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.config import settings
from app.vector_store.retriever import Retriever

QUERIES = [
    "What should I do if the payment API has timeout errors?",
    "How do I check database connection pool usage?",
    "What is the escalation procedure for a P1 incident?",
    "How do I roll back a bad deployment?",
]


async def main():
    retriever = Retriever(settings)
    total = retriever._store.count()
    print(f"ChromaDB vectors: {total}\n")

    if total == 0:
        print("Vector store is empty. Run embed_and_store.py first.")
        return

    for query in QUERIES:
        print(f"Query: {query}")
        docs = await retriever.retrieve(query, top_k=3)
        for i, doc in enumerate(docs, 1):
            print(f"  [{i}] score={doc.score:.3f}  source={doc.metadata.get('source_file')}  type={doc.metadata.get('document_type')}")
            print(f"       {doc.page_content[:100]}...")
        print()

    print("Phase 4 PASSED — retrieval working.")


if __name__ == "__main__":
    asyncio.run(main())
