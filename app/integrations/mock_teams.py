import json
from pathlib import Path
from datetime import datetime
from app.services.logging_service import get_logger

logger = get_logger(__name__)

CHANNELS_FILE = Path("data/mock/teams_channels.json")


def _load_channels() -> list[dict]:
    if not CHANNELS_FILE.exists():
        return []
    return json.loads(CHANNELS_FILE.read_text(encoding="utf-8"))


def get_channels() -> list[dict]:
    return _load_channels()


def get_channel_by_name(name: str) -> dict | None:
    for ch in _load_channels():
        if ch["name"] == name:
            return ch
    return None


def draft_message(
    channel: str,
    content: str,
    incident_id: str | None = None,
    severity: str | None = None,
) -> dict:
    """
    Draft a Teams message for human review.
    Never actually sends — always requires human approval.
    """
    channel_info = get_channel_by_name(channel)
    if not channel_info:
        channel_info = {"name": channel, "channel_id": "unknown"}

    draft = {
        "channel": channel,
        "channel_id": channel_info.get("channel_id"),
        "draft": content,
        "incident_id": incident_id,
        "severity": severity,
        "drafted_at": datetime.utcnow().isoformat() + "Z",
        "requires_human_approval": True,
        "sent": False,
        "status": "draft",
    }

    logger.info(
        "teams_draft_created",
        channel=channel,
        incident_id=incident_id,
        requires_approval=True,
    )
    return draft


def suggest_channel(incident_type: str, severity: str) -> str:
    """Suggest the appropriate Teams channel based on incident type and severity."""
    severity = severity.upper()
    if severity in ("P1",):
        return "operations-alerts"
    if "deployment" in incident_type.lower():
        return "deployments"
    if "payment" in incident_type.lower():
        return "payments-team"
    return "incident-response"
