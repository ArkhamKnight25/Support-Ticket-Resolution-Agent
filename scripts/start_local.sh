#!/bin/bash
# Start the Enterprise AI Ops Copilot locally
set -e

echo "Enterprise AI Ops Copilot - Local Start"
echo "========================================"

# Check .env exists
if [ ! -f ".env" ]; then
  echo "ERROR: .env not found. Run: cp .env.example .env"
  exit 1
fi

# Check venv
if [ ! -d ".venv" ]; then
  echo "Creating virtual environment..."
  python -m venv .venv
fi

# Activate venv
source .venv/bin/activate 2>/dev/null || source .venv/Scripts/activate

# Install deps if needed
pip install -r requirements.txt -q

# Seed and ingest if no chunks exist
if [ ! -d "data/processed/chunks" ] || [ -z "$(ls -A data/processed/chunks 2>/dev/null)" ]; then
  echo "Ingesting documents..."
  python scripts/ingest_documents.py
fi

# Embed and store if ChromaDB is empty
if [ ! -d "chroma_db" ] || [ -z "$(ls -A chroma_db 2>/dev/null)" ]; then
  echo "Embedding and storing chunks..."
  python scripts/embed_and_store.py
fi

echo ""
echo "Starting server at http://localhost:8000"
echo "Swagger UI: http://localhost:8000/docs"
echo ""

python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
