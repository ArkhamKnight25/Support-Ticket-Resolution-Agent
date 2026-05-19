import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import Settings
from app.services.logging_service import get_logger
from app.utils.file_utils import ensure_dir

logger = get_logger(__name__)


class SessionService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._base_dir = ensure_dir(settings.SESSIONS_DIR)

    def _path(self, session_id: str) -> Path:
        safe_session_id = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in session_id)
        return self._base_dir / f"{safe_session_id}.json"

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        path = self._path(session_id)
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            logger.warning("session_corrupt", session_id=session_id, path=str(path))
            return None

    def save_session(self, session_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        data = {
            "session_id": session_id,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            **payload,
        }
        self._path(session_id).write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data

    def append_agent_run(
        self,
        session_id: str,
        *,
        task: str,
        result: dict[str, Any],
    ) -> dict[str, Any]:
        session = self.get_session(session_id) or {
            "session_id": session_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "agent_runs": [],
            "chat_history": [],
        }
        agent_runs = list(session.get("agent_runs", []))
        agent_runs.append(
            {
                "task": task,
                "intent": result.get("intent"),
                "output": result.get("final_answer"),
                "confidence": result.get("confidence"),
                "requires_human_approval": result.get("requires_approval", False),
                "steps": result.get("steps", []),
                "tool_calls": result.get("tool_calls", []),
                "sources": result.get("sources", []),
                "warnings": result.get("warnings", []),
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        session["agent_runs"] = agent_runs[-20:]
        return self.save_session(session_id, session)

    def append_chat_turn(
        self,
        session_id: str,
        *,
        user_message: str,
        assistant_reply: str,
        sources: list[dict[str, Any]],
        warnings: list[str],
        confidence: str | None,
    ) -> dict[str, Any]:
        session = self.get_session(session_id) or {
            "session_id": session_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "agent_runs": [],
            "chat_history": [],
        }
        chat_history = list(session.get("chat_history", []))
        chat_history.append(
            {
                "user": user_message,
                "assistant": assistant_reply,
                "sources": sources,
                "warnings": warnings,
                "confidence": confidence,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        session["chat_history"] = chat_history[-50:]
        return self.save_session(session_id, session)

