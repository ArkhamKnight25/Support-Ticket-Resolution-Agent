import json

from app.config import Settings
from app.services.session_service import SessionService


def test_append_agent_run_persists_json(tmp_path):
    settings = Settings(SESSIONS_DIR=str(tmp_path))
    service = SessionService(settings)

    saved = service.append_agent_run(
        "demo-session",
        task="Summarize the incident",
        result={
            "intent": "incident_analysis",
            "final_answer": "Root cause was database pool exhaustion.",
            "confidence": "high",
            "requires_approval": False,
            "steps": ["classify_intent -> incident_analysis"],
            "tool_calls": [],
            "sources": ["INC-1001"],
            "warnings": [],
        },
    )

    assert saved["session_id"] == "demo-session"
    assert len(saved["agent_runs"]) == 1

    on_disk = json.loads((tmp_path / "demo-session.json").read_text(encoding="utf-8"))
    assert on_disk["agent_runs"][0]["task"] == "Summarize the incident"


def test_append_chat_turn_keeps_recent_history(tmp_path):
    settings = Settings(SESSIONS_DIR=str(tmp_path))
    service = SessionService(settings)

    service.append_chat_turn(
        "chat-session",
        user_message="What happened?",
        assistant_reply="Payment API latency spiked.",
        sources=[{"source_file": "payment_api_runbook.md"}],
        warnings=["Low-confidence response."],
        confidence="low",
    )

    stored = service.get_session("chat-session")
    assert stored is not None
    assert stored["chat_history"][0]["user"] == "What happened?"
    assert stored["chat_history"][0]["confidence"] == "low"
