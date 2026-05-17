from app.integrations.mock_teams import draft_message, get_channels, suggest_channel
from app.services.logging_service import get_logger

logger = get_logger(__name__)


class TeamsTool:
    def draft(
        self,
        channel: str,
        content: str,
        incident_id: str | None = None,
        severity: str | None = None,
    ) -> dict:
        """
        Draft a Teams message. Always returns requires_human_approval=True.
        Used by the LangGraph agent for the communication step.
        """
        return draft_message(
            channel=channel,
            content=content,
            incident_id=incident_id,
            severity=severity,
        )

    def suggest_channel(self, incident_type: str, severity: str = "P2") -> str:
        """Suggest the right Teams channel for an incident."""
        return suggest_channel(incident_type, severity)

    def list_channels(self) -> list[dict]:
        return get_channels()

    def draft_incident_update(
        self,
        service: str,
        summary: str,
        recommended_actions: list[str],
        severity: str = "P2",
        incident_id: str | None = None,
    ) -> dict:
        """
        Compose and draft a structured incident update message.
        Used by the LangGraph agent's teams_draft_node.
        """
        actions_text = "\n".join(f"• {a}" for a in recommended_actions)
        content = (
            f"🚨 **{severity} Incident Update — {service}**\n\n"
            f"{summary}\n\n"
            f"**Recommended Actions:**\n{actions_text}\n\n"
            f"_This message requires human approval before sending._"
        )
        channel = suggest_channel(service, severity)
        return self.draft(
            channel=channel,
            content=content,
            incident_id=incident_id,
            severity=severity,
        )
