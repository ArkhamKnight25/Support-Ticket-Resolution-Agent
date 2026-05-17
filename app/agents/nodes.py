"""
LangGraph node functions.
Each node receives AgentState, performs one unit of work, and returns a partial state update.
"""
import re
from app.agents.state import AgentState
from app.services.logging_service import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Intent classification — rule-based (no Bedrock quota needed)
# ---------------------------------------------------------------------------

_INTENT_RULES = [
    ("communication_request", [
        r"\bdraft\b", r"\bwrite\b", r"\bnotif", r"\bteams\b", r"\bslack\b",
        r"\bupdate the team\b", r"\bsend (a|an) (message|update|alert)\b",
        r"\bcommunicat", r"\bannounce",
    ]),
    ("incident_analysis", [
        r"\bincidents?\b",           # singular and plural
        r"\btickets?\b",
        r"\bpast (issue|incident|problem|error)",
        r"\bsimilar (issue|incident|problem|error)",
        r"\broot cause\b",
        r"\bprevious\b.*\b(issue|incident|error)",
        r"\bhistor",
        r"\bINC-\d+",
        r"\bfind (past|similar|related|all)",
        r"\bshow me (all|past|similar|related)",
        r"\bwas there (a|an)",
    ]),
    ("metrics_question", [
        r"\bmetric", r"\blatency\b", r"\berror rate\b", r"\bdegraded\b",
        r"\bwas (it|the service|.+api)\b", r"\bhealthy\b",
        r"\bstatus\b.*\bservice\b", r"\brequest count\b",
        r"\bthroughput\b", r"\bp99\b", r"\bp50\b",
        r"\bshow me.*(metric|performance|latency)",
    ]),
    ("document_question", [
        r"\brunbook\b", r"\bpolicy\b", r"\bpolicies\b",
        r"\bprocedure\b", r"\bchecklist\b",
        r"\bhow (do|should|can) (i|we|the team)\b",
        r"\bwhat should\b", r"\bwhat are the\b",
        r"\bsteps (to|for)\b", r"\bguide\b", r"\bdocument",
        r"\brequirement", r"\bretention\b",
        r"\bmonitoring alert", r"\balert.*(trigger|threshold|fire)",
        r"\bbefore (a |the )?(deployment|deploy|release)\b",
    ]),
]


def _rule_based_classify(question: str) -> str:
    q = question.lower()
    for intent, patterns in _INTENT_RULES:
        for pat in patterns:
            if re.search(pat, q):
                return intent
    return "general_ai_question"


def _add_step(state: AgentState, step: str) -> list[str]:
    return list(state.get("steps", [])) + [step]


def _add_tool_call(state: AgentState, tool: str, input_data: dict, output: any) -> list[dict]:
    return list(state.get("tool_calls", [])) + [
        {"tool": tool, "input": input_data, "output": str(output)[:200]}
    ]


# ---------------------------------------------------------------------------
# Node functions
# ---------------------------------------------------------------------------

async def classify_intent_node(state: AgentState) -> AgentState:
    question = state["messages"][-1]["content"]
    intent = _rule_based_classify(question)
    logger.info("intent_classified", intent=intent, question=question[:60])
    return {
        **state,
        "intent": intent,
        "steps": _add_step(state, f"classify_intent -> {intent}"),
    }


async def rag_search_node(state: AgentState) -> AgentState:
    from app.config import settings
    from app.services.rag_service import RAGService
    from app.services.embedding_service import EmbeddingService

    question = state["messages"][-1]["content"]
    rag = RAGService(settings, EmbeddingService(settings))

    docs = await rag.retrieve(question, top_k=4)
    doc_dicts = [
        {"text": d.page_content, "source": d.metadata.get("source_file"), "score": d.score}
        for d in docs
    ]

    logger.info("rag_search_complete", docs=len(doc_dicts))
    return {
        **state,
        "retrieved_docs": doc_dicts,
        "steps": _add_step(state, f"rag_search -> {len(doc_dicts)} docs"),
        "tool_calls": _add_tool_call(state, "rag_tool", {"query": question}, doc_dicts),
    }


async def ticket_search_node(state: AgentState) -> AgentState:
    from app.tools.ticket_tool import TicketTool

    question = state["messages"][-1]["content"]
    tool = TicketTool()

    # Extract service hint from the question
    service = None
    for svc in ["payment-api", "auth-service", "database", "notification-service"]:
        if svc.replace("-", " ") in question.lower() or svc in question.lower():
            service = svc
            break

    tickets = await tool.search(query=question, service=service, limit=5)
    ticket_dicts = [t.model_dump(mode="json") for t in tickets]

    logger.info("ticket_search_complete", tickets=len(ticket_dicts), service=service)
    return {
        **state,
        "tickets": ticket_dicts,
        "steps": _add_step(state, f"ticket_search -> {len(ticket_dicts)} tickets"),
        "tool_calls": _add_tool_call(state, "ticket_tool", {"query": question, "service": service}, ticket_dicts),
    }


async def sql_query_node(state: AgentState) -> AgentState:
    from app.tools.sql_tool import SQLTool

    question = state["messages"][-1]["content"]
    tool = SQLTool()

    service = None
    for svc in ["payment-api", "auth-service", "database", "notification-service"]:
        if svc.replace("-", " ") in question.lower() or svc in question.lower():
            service = svc
            break

    if service:
        metrics = tool.query(service=service, status="degraded", limit=10)
        if not metrics:
            metrics = tool.query(service=service, limit=10)
    else:
        metrics = tool.degraded_events()[:10]

    logger.info("sql_query_complete", rows=len(metrics), service=service)
    return {
        **state,
        "metrics": metrics,
        "steps": _add_step(state, f"sql_query -> {len(metrics)} rows"),
        "tool_calls": _add_tool_call(state, "sql_tool", {"service": service}, metrics),
    }


async def teams_draft_node(state: AgentState) -> AgentState:
    from app.tools.teams_tool import TeamsTool

    question = state["messages"][-1]["content"]
    tool = TeamsTool()

    # Build a summary from gathered evidence
    tickets = state.get("tickets", [])
    metrics = state.get("metrics", [])
    docs = state.get("retrieved_docs", [])

    service = "service"
    for svc in ["payment-api", "auth-service", "database", "notification-service"]:
        if svc.replace("-", " ") in question.lower() or svc in question.lower():
            service = svc
            break

    summary_parts = []
    if tickets:
        t = tickets[0]
        summary_parts.append(
            f"Similar past incident {t.get('ticket_id')}: {t.get('title')}. "
            f"Root cause: {t.get('root_cause', 'unknown')}."
        )
    if metrics:
        m = metrics[0]
        summary_parts.append(
            f"Latest metrics: latency={m.get('latency_ms')}ms, "
            f"error_rate={m.get('error_rate')}%, status={m.get('status')}."
        )
    if docs:
        summary_parts.append(f"Runbook guidance retrieved from {docs[0].get('source')}.")

    summary = " ".join(summary_parts) if summary_parts else f"Issue detected on {service}."

    actions = [
        "Investigate database connection pool usage",
        "Check service latency metrics",
        "Review recent deployments",
        "Escalate if not resolved in 15 minutes",
    ]

    draft = tool.draft_incident_update(
        service=service,
        summary=summary,
        recommended_actions=actions,
        severity="P2",
    )

    logger.info("teams_draft_complete", channel=draft.get("channel"))
    return {
        **state,
        "draft_message": draft,
        "requires_approval": True,
        "recommended_actions": actions,
        "steps": _add_step(state, f"teams_draft -> #{draft.get('channel')}"),
        "tool_calls": _add_tool_call(state, "teams_tool", {"service": service}, draft),
    }


async def evidence_merge_node(state: AgentState) -> AgentState:
    parts = []

    docs = state.get("retrieved_docs", [])
    if docs:
        parts.append("=== Documents Retrieved ===")
        for d in docs[:3]:
            parts.append(f"Source: {d.get('source')} (score: {d.get('score', 0):.2f})")
            parts.append(d.get("text", "")[:300])

    tickets = state.get("tickets", [])
    if tickets:
        parts.append("\n=== Related Incidents ===")
        for t in tickets[:3]:
            parts.append(
                f"[{t.get('ticket_id')}] {t.get('title')} | "
                f"Priority: {t.get('priority')} | Status: {t.get('status')}"
            )
            if t.get("root_cause"):
                parts.append(f"  Root cause: {t.get('root_cause')}")
            if t.get("resolution"):
                parts.append(f"  Resolution: {t.get('resolution')}")

    metrics = state.get("metrics", [])
    if metrics:
        parts.append("\n=== Service Metrics ===")
        for m in metrics[:5]:
            date = str(m.get("date", ""))[:10]
            parts.append(
                f"{date} | {m.get('service_name')} | "
                f"latency={m.get('latency_ms')}ms | "
                f"error={m.get('error_rate')}% | "
                f"status={m.get('status')}"
            )

    evidence = "\n".join(parts) if parts else "No evidence gathered."
    logger.info("evidence_merged", sources=len(parts))

    return {
        **state,
        "evidence_summary": evidence,
        "steps": _add_step(state, "evidence_merge"),
    }


async def guardrail_node(state: AgentState) -> AgentState:
    from app.services.guardrail_service import GuardrailService
    from app.config import settings

    guardrail = GuardrailService(settings)
    question = state["messages"][-1]["content"]
    blocked = await guardrail.check_input(question)

    if blocked:
        return {
            **state,
            "final_answer": "I cannot process this request as it violates content policy.",
            "confidence": "high",
            "warnings": ["Request blocked by content policy."],
            "steps": _add_step(state, "guardrail -> BLOCKED"),
        }

    confidence = "low"
    has_docs = bool(state.get("retrieved_docs"))
    has_tickets = bool(state.get("tickets"))
    has_metrics = bool(state.get("metrics"))

    if (has_docs and has_tickets) or (has_docs and has_metrics):
        confidence = "high"
    elif has_docs or has_tickets or has_metrics:
        confidence = "medium"

    return {
        **state,
        "confidence": confidence,
        "warnings": [] if confidence != "low" else ["Low-confidence evidence set."],
        "steps": _add_step(state, f"guardrail -> passed (confidence={confidence})"),
    }


async def final_response_node(state: AgentState) -> AgentState:
    from app.services.bedrock_service import BedrockService
    from app.services.guardrail_service import GuardrailService
    from app.agents.prompts import FINAL_RESPONSE_PROMPT
    from app.config import settings

    if state.get("final_answer"):
        return state

    question = state["messages"][-1]["content"]
    evidence = state.get("evidence_summary", "No evidence gathered.")

    prompt = FINAL_RESPONSE_PROMPT.format(question=question, evidence=evidence)

    bedrock = BedrockService(settings)
    guardrail = GuardrailService(settings)
    try:
        response = await bedrock.chat(message=prompt, context_docs=[], history=[])
        answer = response.content
        grounding_context = state.get("retrieved_docs", []) or [{"text": evidence}]
        output_flagged = await guardrail.check_output(answer, grounding_context)
        if output_flagged:
            answer = _build_fallback_answer(state, question)
    except Exception as e:
        # Graceful fallback when Bedrock is throttled
        answer = _build_fallback_answer(state, question)
        logger.warning("bedrock_unavailable_using_fallback", error=str(e)[:80])

    warnings = list(state.get("warnings", []))
    if state.get("requires_approval"):
        warnings.append("External communication requires human approval before sending.")

    return {
        **state,
        "final_answer": answer,
        "warnings": list(dict.fromkeys(warnings)),
        "sources": _collect_sources(state),
        "recommended_actions": state.get("recommended_actions", _default_recommended_actions()),
        "steps": _add_step(state, "final_response"),
    }


def _build_fallback_answer(state: AgentState, question: str) -> str:
    """Build a structured answer directly from gathered evidence (no LLM needed)."""
    lines = [f"**Summary** (evidence-based, LLM unavailable due to quota limit)\n"]

    tickets = state.get("tickets", [])
    if tickets:
        t = tickets[0]
        lines.append(f"Most relevant past incident: **{t.get('ticket_id')}** — {t.get('title')}")
        lines.append(f"- Root cause: {t.get('root_cause', 'N/A')}")
        lines.append(f"- Resolution: {t.get('resolution', 'N/A')}")

    metrics = state.get("metrics", [])
    if metrics:
        m = metrics[0]
        lines.append(f"\nLatest metric snapshot ({str(m.get('date',''))[:10]}):")
        lines.append(f"- Service: {m.get('service_name')} | Status: {m.get('status')}")
        lines.append(f"- Latency: {m.get('latency_ms')}ms | Error rate: {m.get('error_rate')}%")

    docs = state.get("retrieved_docs", [])
    if docs:
        lines.append(f"\nRelevant documentation found in: {docs[0].get('source')}")

    lines.append("\n**Recommended Actions:**")
    for action in state.get("recommended_actions", _default_recommended_actions()):
        lines.append(f"- {action}")

    lines.append(f"\n**Confidence:** {state.get('confidence', 'medium')}")
    if state.get("requires_approval"):
        lines.append("⚠️ Teams message requires human approval before sending.")

    return "\n".join(lines)


def _default_recommended_actions() -> list[str]:
    return [
        "Check database connection pool usage",
        "Review recent deployments for regressions",
        "Check external gateway status pages",
        "Escalate to on-call engineer if not resolved in 15 minutes",
    ]


def _collect_sources(state: AgentState) -> list[str]:
    sources = [doc.get("source") for doc in state.get("retrieved_docs", []) if doc.get("source")]
    sources.extend(ticket.get("ticket_id") for ticket in state.get("tickets", []) if ticket.get("ticket_id"))
    return list(dict.fromkeys(sources))
