from app.integrations.mock_snowflake import query_metrics, get_service_summary, get_degraded_events
from app.services.logging_service import get_logger

logger = get_logger(__name__)


class SQLTool:
    def query(
        self,
        service: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        status: str | None = None,
        limit: int = 20,
    ) -> list[dict]:
        """Query operational metrics. Used by the LangGraph agent."""
        return query_metrics(service=service, date_from=date_from, date_to=date_to, status=status, limit=limit)

    def summarize(self, service: str) -> dict:
        """Get aggregate stats for a service."""
        return get_service_summary(service)

    def degraded_events(self, service: str | None = None) -> list[dict]:
        """Return all degraded periods, optionally filtered by service."""
        return get_degraded_events(service=service)

    def was_degraded_on(self, service: str, date: str) -> dict:
        """Check if a specific service was degraded on a specific date."""
        rows = query_metrics(service=service, date_from=date, date_to=date)
        if not rows:
            return {"found": False, "service": service, "date": date}
        row = rows[0]
        return {
            "found": True,
            "service": service,
            "date": date,
            "status": row.get("status"),
            "error_rate": row.get("error_rate"),
            "latency_ms": row.get("latency_ms"),
            "request_count": row.get("request_count"),
        }
