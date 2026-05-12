from pydantic import BaseModel, Field
from typing import Optional


class HistoryMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    session_id: Optional[str] = None
    history: list[HistoryMessage] = Field(default_factory=list)


class SourceMetadata(BaseModel):
    source_file: Optional[str] = None
    document_type: Optional[str] = None
    chunk_id: Optional[str] = None


class ChatResponse(BaseModel):
    reply: str
    sources: list[SourceMetadata] = Field(default_factory=list)
    model: str
    session_id: Optional[str] = None
    confidence: Optional[str] = None
    warnings: list[str] = Field(default_factory=list)


class ChatHistory(BaseModel):
    session_id: str
    messages: list[HistoryMessage] = Field(default_factory=list)
