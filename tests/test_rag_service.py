import pytest
from pathlib import Path
from app.data_pipeline.document_loader import load_file, discover_documents
from app.data_pipeline.chunker import chunk_text
from app.data_pipeline.metadata_extractor import extract_metadata
from app.data_pipeline.quality_checks import is_valid_chunk, filter_chunks


# ── Document loader ────────────────────────────────────────────────────────

def test_discover_documents():
    docs = discover_documents("data/raw")
    assert len(docs) >= 5


def test_load_markdown_file():
    path = Path("data/raw/runbooks/payment_api_runbook.md")
    text = load_file(path)
    assert len(text) > 100
    assert "payment" in text.lower()


def test_load_nonexistent_returns_empty():
    text = load_file(Path("data/raw/nonexistent.md"))
    assert text == ""


# ── Chunker ────────────────────────────────────────────────────────────────

def test_chunk_produces_output():
    text = "This is a test document. " * 50
    chunks = chunk_text(text, chunk_size=200, chunk_overlap=20)
    assert len(chunks) > 1


def test_chunk_respects_size():
    text = "Word " * 500
    chunks = chunk_text(text, chunk_size=100, chunk_overlap=10)
    for chunk in chunks:
        assert len(chunk.text) <= 150  # allow some tolerance


def test_chunk_index_sequential():
    text = "Sentence number one. Sentence number two. " * 30
    chunks = chunk_text(text, chunk_size=100, chunk_overlap=10)
    indices = [c.chunk_index for c in chunks]
    assert indices == list(range(len(chunks)))


def test_chunk_empty_text():
    chunks = chunk_text("", chunk_size=500)
    assert chunks == []


# ── Quality checks ─────────────────────────────────────────────────────────

def test_valid_chunk_passes():
    assert is_valid_chunk("This is a meaningful sentence with enough content to pass.") is True


def test_too_short_chunk_fails():
    assert is_valid_chunk("Hi") is False


def test_whitespace_chunk_fails():
    assert is_valid_chunk("   \n\n\t   \n   ") is False


def test_filter_chunks_removes_bad():
    from app.data_pipeline.chunker import TextChunk
    chunks = [
        TextChunk(text="Short", chunk_index=0),
        TextChunk(text="This is a valid chunk with enough content to pass quality checks.", chunk_index=1),
        TextChunk(text="   ", chunk_index=2),
    ]
    result = filter_chunks(chunks)
    assert len(result) == 1
    assert result[0].chunk_index == 1


# ── Metadata extractor ─────────────────────────────────────────────────────

def test_metadata_policy_type():
    path = Path("data/raw/policies/database_incident_policy.md")
    meta = extract_metadata(path, chunk_index=0, chunk_id="test_001")
    assert meta["document_type"] == "policy"


def test_metadata_runbook_type():
    path = Path("data/raw/runbooks/payment_api_runbook.md")
    meta = extract_metadata(path, chunk_index=0, chunk_id="test_002")
    assert meta["document_type"] == "runbook"
    assert meta["service"] == "payment-api"


def test_metadata_contains_required_fields():
    path = Path("data/raw/runbooks/deployment_checklist.md")
    meta = extract_metadata(path, chunk_index=2, chunk_id="abc_chunk_0002")
    assert "chunk_id" in meta
    assert "source_file" in meta
    assert "chunk_index" in meta
    assert meta["chunk_index"] == 2
