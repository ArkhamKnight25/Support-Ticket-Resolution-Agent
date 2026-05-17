from fastapi import APIRouter, Depends, HTTPException
from app.schemas.agent_schema import AgentRequest, AgentResponse, ToolCallRecord, EvidenceSummary
from app.agents.graph import build_agent_graph
from app.agents.state import AgentState
from app.dependencies import get_session_service, require_api_key
from app.services.session_service import SessionService

router = APIRouter()

# Build once at startup (avoid rebuilding on every request)
_graph = None


def _get_graph():
    global _graph
    if _graph is None:
        _graph = build_agent_graph()
    return _graph


@router.post("/run", response_model=AgentResponse)
async def run_agent(
    request: AgentRequest,
    session_service: SessionService = Depends(get_session_service),
    _: None = Depends(require_api_key),
):
    graph = _get_graph()
    initial_state: AgentState = {
        "messages": [{"role": "user", "content": request.task}],
        "session_id": request.session_id,
        "metadata": request.metadata or {},
        "steps": [],
        "tool_calls": [],
        "retrieved_docs": [],
        "tickets": [],
        "metrics": [],
        "warnings": [],
    }

    try:
        result = await graph.ainvoke(initial_state)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    tool_calls = [
        ToolCallRecord(
            tool=tc.get("tool", ""),
            input=tc.get("input", {}),
            output=tc.get("output"),
        )
        for tc in result.get("tool_calls", [])
    ]

    sources = list(dict.fromkeys(result.get("sources", [])))
    evidence = EvidenceSummary(
        documents=[doc.get("source") for doc in result.get("retrieved_docs", []) if doc.get("source")],
        tickets=[ticket.get("ticket_id") for ticket in result.get("tickets", []) if ticket.get("ticket_id")],
        metrics=result.get("metrics", [])[:5],
    )
    response = AgentResponse(
        session_id=request.session_id,
        intent=result.get("intent"),
        output=result.get("final_answer", "No answer generated."),
        steps=result.get("steps", []),
        tool_calls=tool_calls,
        confidence=result.get("confidence"),
        requires_human_approval=result.get("requires_approval", False),
        recommended_actions=result.get("recommended_actions", []),
        sources=sources,
        warnings=result.get("warnings", []),
        teams_draft=(result.get("draft_message") or {}).get("draft"),
        evidence=evidence,
    )
    session_service.append_agent_run(
        request.session_id,
        task=request.task,
        result={
            **result,
            "sources": sources,
        },
    )
    return response


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    session_service: SessionService = Depends(get_session_service),
    _: None = Depends(require_api_key),
):
    session = session_service.get_session(session_id)
    if session is None:
        return {"session_id": session_id, "status": "not_found"}
    return session
