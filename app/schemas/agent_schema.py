from pydantic import BaseModel, Field
from typing import Optional, Any


class AgentRequest(BaseModel):
    task: str = Field(..., min_length=1, max_length=4000)
    session_id: str = Field(default="default")
    metadata: Optional[dict[str, Any]] = None


class ToolCallRecord(BaseModel):
    tool: str
    input: dict[str, Any] = Field(default_factory=dict)
    output: Optional[Any] = None


class EvidenceSummary(BaseModel):
    documents: list[str] = Field(default_factory=list)
    tickets: list[str] = Field(default_factory=list)
    metrics: list[dict[str, Any]] = Field(default_factory=list)


class AgentResponse(BaseModel):
    session_id: str
    intent: Optional[str] = None
    output: str
    steps: list[str] = Field(default_factory=list)
    tool_calls: list[ToolCallRecord] = Field(default_factory=list)
    confidence: Optional[str] = None
    requires_human_approval: bool = False
    recommended_actions: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    teams_draft: Optional[str] = None
    evidence: EvidenceSummary = Field(default_factory=EvidenceSummary)
