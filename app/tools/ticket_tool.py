from app.integrations.mock_servicenow import search_tickets, get_ticket, create_ticket, update_ticket
from app.schemas.ticket_schema import TicketCreate, TicketResponse, TicketUpdate
from app.services.logging_service import get_logger

logger = get_logger(__name__)


def _to_response(t: dict) -> TicketResponse:
    from datetime import datetime

    def _parse_dt(val):
        if not val:
            return None
        try:
            return datetime.fromisoformat(val.replace("Z", "+00:00"))
        except Exception:
            return None

    return TicketResponse(
        ticket_id=t["ticket_id"],
        title=t["title"],
        description=t.get("description", ""),
        priority=t.get("priority", "P3"),
        status=t.get("status", "Open"),
        service=t.get("service"),
        root_cause=t.get("root_cause"),
        resolution=t.get("resolution"),
        created_at=_parse_dt(t.get("created_at")),
        resolved_at=_parse_dt(t.get("resolved_at")),
    )


class TicketTool:
    async def create_ticket(self, ticket: TicketCreate) -> TicketResponse:
        data = ticket.model_dump(exclude_none=True)
        result = create_ticket(data)
        return _to_response(result)

    async def list_tickets(
        self,
        status: str | None = None,
        priority: str | None = None,
        limit: int = 20,
    ) -> list[TicketResponse]:
        results = search_tickets(status=status, priority=priority, limit=limit)
        return [_to_response(t) for t in results]

    async def get_ticket(self, ticket_id: str) -> TicketResponse | None:
        t = get_ticket(ticket_id)
        return _to_response(t) if t else None

    async def update_ticket(self, ticket_id: str, update: TicketUpdate) -> TicketResponse | None:
        updates = update.model_dump(exclude_none=True)
        result = update_ticket(ticket_id, updates)
        return _to_response(result) if result else None

    async def search(self, query: str, service: str | None = None, limit: int = 5) -> list[TicketResponse]:
        """Used by the LangGraph agent to search tickets by keyword."""
        results = search_tickets(query=query, service=service, limit=limit)
        return [_to_response(t) for t in results]
