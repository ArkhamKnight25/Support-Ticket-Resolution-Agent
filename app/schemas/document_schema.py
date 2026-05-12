from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class DocumentMeta(BaseModel):
    document_id: str
    filename: str
    document_type: Optional[str] = None
    chunk_count: Optional[int] = None
    ingested_at: Optional[datetime] = None
    indexed: bool = False


class DocumentIngestionResponse(BaseModel):
    document_id: str
    filename: str
    document_type: Optional[str] = None
    chunk_count: int = 0
    indexed: bool = False
    status: str  # queued | processing | complete | failed


class DocumentListResponse(BaseModel):
    documents: list[DocumentMeta] = Field(default_factory=list)
    total: int
