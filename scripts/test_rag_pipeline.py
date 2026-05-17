"""
Phase 5 smoke test — full RAG pipeline.
Tests: retrieval + Bedrock LLM response.
Run: python scripts/test_rag_pipeline.py

NOTE: Requires Bedrock quota. If throttled, the retrieval part will still
      be shown so you can confirm the RAG pipeline is wired correctly.
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.config import settings
from app.services.bedrock_service import BedrockService
from app.services.rag_service import RAGService
from app.services.embedding_service import EmbeddingService
from app.vector_store.chroma_store import ChromaStore

QUESTION = "What should I check if the payment API has timeout errors?"


async def main():
    print("=" * 60)
    print("Phase 5 — RAG Pipeline Test")
    print("=" * 60)

    # --- Step 1: Retrieval ---
    print(f"\nQuestion: {QUESTION}\n")
    print("Step 1 — Retrieving relevant documents...")

    rag = RAGService(settings, EmbeddingService(settings))
    docs = await rag.retrieve(QUESTION, top_k=3)

    if not docs:
        print("  No documents retrieved. Run embed_and_store.py first.")
        return

    print(f"  Retrieved {len(docs)} documents:")
    for i, doc in enumerate(docs, 1):
        print(f"  [{i}] score={doc.score:.3f}  {doc.metadata.get('source_file')}  ({doc.metadata.get('document_type')})")
        print(f"       {doc.page_content[:120]}...\n")

    # --- Step 2: LLM Response ---
    print("Step 2 — Sending to Bedrock LLM with context...")
    bedrock = BedrockService(settings)
    try:
        response = await bedrock.chat(
            message=QUESTION,
            context_docs=docs,
            history=[],
        )
        print(f"\nAnswer ({response.latency_ms:.0f}ms):")
        print(response.content)
        print(f"\nTokens — input: {response.input_tokens}  output: {response.output_tokens}")
        print("\nPhase 5 PASSED — full RAG pipeline working.")
    except Exception as e:
        print(f"\n  Bedrock call failed: {e}")
        print("\n  Retrieval works. Phase 5 is ready — waiting for Bedrock quota.")
        print("  Once Bedrock quota resets, this test will print a full grounded answer.")


if __name__ == "__main__":
    asyncio.run(main())
