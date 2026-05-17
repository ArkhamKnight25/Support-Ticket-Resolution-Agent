from langgraph.graph import StateGraph, END, START
from app.agents.state import AgentState
from app.agents.nodes import (
    classify_intent_node,
    rag_search_node,
    ticket_search_node,
    sql_query_node,
    teams_draft_node,
    evidence_merge_node,
    guardrail_node,
    final_response_node,
)


def _route_intent(state: AgentState) -> str:
    """Conditional edge: route to first tool based on classified intent."""
    intent = state.get("intent", "general_ai_question")
    routes = {
        "document_question":    "rag_search",
        "incident_analysis":    "ticket_search",
        "metrics_question":     "sql_query",
        "communication_request":"ticket_search",   # gather evidence first
        "general_ai_question":  "evidence_merge",
    }
    return routes.get(intent, "evidence_merge")


def _route_after_tickets(state: AgentState) -> str:
    """After ticket search, decide whether to also pull docs and metrics."""
    intent = state.get("intent", "general_ai_question")
    if intent in ("incident_analysis", "communication_request"):
        return "rag_search_secondary"
    return "evidence_merge"


def _route_after_rag_secondary(state: AgentState) -> str:
    intent = state.get("intent", "general_ai_question")
    if intent in ("incident_analysis", "communication_request"):
        return "sql_query"
    return "evidence_merge"


def _route_after_sql(state: AgentState) -> str:
    intent = state.get("intent", "general_ai_question")
    if intent == "communication_request":
        return "teams_draft"
    return "evidence_merge"


def _check_blocked(state: AgentState) -> str:
    """After guardrail, go straight to end if blocked, else generate response."""
    if state.get("final_answer"):
        return END
    return "final_response"


def build_agent_graph():
    """
    Build and compile the LangGraph agent workflow.

    Flow:
        START → classify_intent
          ↓ (route by intent)
        document_question      → rag_search → evidence_merge
        incident_analysis      → ticket_search → rag_search_secondary → sql_query → evidence_merge
        metrics_question       → sql_query → evidence_merge
        communication_request  → ticket_search → rag_search_secondary → sql_query → teams_draft → evidence_merge
        general_ai_question    → evidence_merge
          ↓
        guardrail → final_response → END
    """
    graph = StateGraph(AgentState)

    # Register nodes
    graph.add_node("classify_intent",      classify_intent_node)
    graph.add_node("rag_search",           rag_search_node)
    graph.add_node("rag_search_secondary", rag_search_node)   # reuse same function
    graph.add_node("ticket_search",        ticket_search_node)
    graph.add_node("sql_query",            sql_query_node)
    graph.add_node("teams_draft",          teams_draft_node)
    graph.add_node("evidence_merge",       evidence_merge_node)
    graph.add_node("guardrail",            guardrail_node)
    graph.add_node("final_response",       final_response_node)

    # Entry
    graph.add_edge(START, "classify_intent")

    # Intent routing
    graph.add_conditional_edges(
        "classify_intent",
        _route_intent,
        {
            "rag_search":           "rag_search",
            "ticket_search":        "ticket_search",
            "sql_query":            "sql_query",
            "evidence_merge":       "evidence_merge",
        },
    )

    # After primary RAG (document_question)
    graph.add_edge("rag_search", "evidence_merge")

    # After ticket search
    graph.add_conditional_edges(
        "ticket_search",
        _route_after_tickets,
        {
            "rag_search_secondary": "rag_search_secondary",
            "evidence_merge":       "evidence_merge",
        },
    )

    # After secondary RAG (incident_analysis / communication)
    graph.add_conditional_edges(
        "rag_search_secondary",
        _route_after_rag_secondary,
        {
            "sql_query":      "sql_query",
            "evidence_merge": "evidence_merge",
        },
    )

    # After SQL
    graph.add_conditional_edges(
        "sql_query",
        _route_after_sql,
        {
            "teams_draft":    "teams_draft",
            "evidence_merge": "evidence_merge",
        },
    )

    # Teams draft always goes to evidence_merge
    graph.add_edge("teams_draft", "evidence_merge")

    # Evidence → guardrail → final
    graph.add_edge("evidence_merge", "guardrail")
    graph.add_conditional_edges(
        "guardrail",
        _check_blocked,
        {
            "final_response": "final_response",
            END: END,
        },
    )
    graph.add_edge("final_response", END)

    return graph.compile()
