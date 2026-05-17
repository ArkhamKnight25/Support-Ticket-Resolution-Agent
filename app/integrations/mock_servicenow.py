import json
from pathlib import Path
from datetime import datetime
from app.services.logging_service import get_logger

logger = get_logger(__name__)

TICKETS_FILE = Path("data/mock/tickets.json")


def _load_tickets() -> list[dict]:
    if not TICKETS_FILE.exists():
        logger.warning("tickets.json not found", path=str(TICKETS_FILE))
        return []
    return json.loads(TICKETS_FILE.read_text(encoding="utf-8"))


def search_tickets(
    query: str = "",
    service: str | None = None,
    priority: str | None = None,
    status: str | None = None,
    limit: int = 10,
) -> list[dict]:
    """Search mock ServiceNow tickets by keyword, service, priority, or status."""
    tickets = _load_tickets()

    if service:
        tickets = [t for t in tickets if t.get("service") == service]
    if priority:
        tickets = [t for t in tickets if t.get("priority") == priority]
    if status:
        tickets = [t for t in tickets if t.get("status", "").lower() == status.lower()]

    if query:
        # Split into keywords and match any of them
        keywords = [w for w in query.lower().split() if len(w) > 3]
        def _matches(t: dict) -> bool:
            haystack = " ".join([
                t.get("title", ""), t.get("description", ""),
                t.get("root_cause", ""), " ".join(t.get("tags", []))
            ]).lower()
            return any(kw in haystack for kw in keywords)
        tickets = [t for t in tickets if _matches(t)]

    logger.info("ticket_search", query=query, results=len(tickets[:limit]))
    return tickets[:limit]


def get_ticket(ticket_id: str) -> dict | None:
    tickets = _load_tickets()
    for t in tickets:
        if t["ticket_id"] == ticket_id:
            return t
    return None


def create_ticket(data: dict) -> dict:
    tickets = _load_tickets()
    new_id = f"INC-{1000 + len(tickets) + 1}"
    ticket = {
        "ticket_id": new_id,
        "status": "Open",
        "created_at": datetime.utcnow().isoformat() + "Z",
        "resolved_at": None,
        **data,
    }
    tickets.append(ticket)
    TICKETS_FILE.write_text(json.dumps(tickets, indent=2), encoding="utf-8")
    logger.info("ticket_created", ticket_id=new_id)
    return ticket


def update_ticket(ticket_id: str, updates: dict) -> dict | None:
    tickets = _load_tickets()
    for i, t in enumerate(tickets):
        if t["ticket_id"] == ticket_id:
            tickets[i] = {**t, **updates}
            TICKETS_FILE.write_text(json.dumps(tickets, indent=2), encoding="utf-8")
            return tickets[i]
    return None
