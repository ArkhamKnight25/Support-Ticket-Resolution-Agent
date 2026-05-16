from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from app.schemas.document_schema import DocumentIngestionResponse, DocumentListResponse
from app.data_pipeline.ingestion_pipeline import IngestionPipeline
from app.services.embedding_service import EmbeddingService
from app.dependencies import get_embedding_service, require_api_key

router = APIRouter()


def get_pipeline(embedding_service: EmbeddingService = Depends(get_embedding_service)):
    return IngestionPipeline(embedding_service)


@router.post("/ingest", response_model=DocumentIngestionResponse)
async def ingest_document(
    file: UploadFile = File(...),
    pipeline: IngestionPipeline = Depends(get_pipeline),
    _: None = Depends(require_api_key),
):
    if file.content_type not in ["application/pdf", "text/plain", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]:
        raise HTTPException(status_code=415, detail="Unsupported file type.")

    content = await file.read()
    result = await pipeline.ingest_bytes(content, filename=file.filename)

    return DocumentIngestionResponse(**result)


@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    pipeline: IngestionPipeline = Depends(get_pipeline),
    _: None = Depends(require_api_key),
):
    docs = await pipeline.list_documents()
    return DocumentListResponse(documents=docs, total=len(docs))


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    pipeline: IngestionPipeline = Depends(get_pipeline),
    _: None = Depends(require_api_key),
):
    deleted = await pipeline.delete_document(document_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found.")
    return {"status": "deleted", "document_id": document_id}
