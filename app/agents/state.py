from typing import TypedDict, Any, Optional


class AgentState(TypedDict, total=False):
    # Core
    messages: list[dict]
    session_id: str
    metadata: dict[str, Any]

    # Intent classification
    intent: str  # document_question | incident_analysis | metrics_question | communication_request | general_ai_question

    # Tool outputs
    retrieved_docs: list[dict]   # from RAG
    tickets: list[dict]          # from ServiceNow
    metrics: list[dict]          # from Snowflake/SQL
    draft_message: dict          # from Teams

    # Merged evidence for final prompt
    evidence_summary: str

    # Final output
    final_answer: str
    confidence: str              # high | medium | low
    requires_approval: bool
    recommended_actions: list[str]
    warnings: list[str]
    sources: list[str]

    # Observability
    steps: list[str]
    tool_calls: list[dict]
