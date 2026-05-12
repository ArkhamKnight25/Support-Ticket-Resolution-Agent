from pydantic import BaseModel, Field
from typing import Optional


class EvaluationRequest(BaseModel):
    question: str = Field(..., min_length=1)
    expected_answer: Optional[str] = None
    expected_source: Optional[str] = None
    expected_keywords: list[str] = []
    category: Optional[str] = None
    difficulty: Optional[str] = None


class EvaluationResponse(BaseModel):
    question: str
    generated_answer: str
    expected_answer: Optional[str] = None
    keyword_match_score: float = 0.0
    retrieval_hit: bool = False
    latency_ms: float = 0.0
    passed: bool = False
    notes: Optional[str] = None


class EvaluationBatchResponse(BaseModel):
    results: list[EvaluationResponse]
    total: int
    passed: int = 0
    failed: int = 0
    avg_latency_ms: float = 0.0
