import pytest
from app.integrations.mock_servicenow import search_tickets, get_ticket, _load_tickets
from app.tools.ticket_tool import TicketTool
from app.schemas.ticket_schema import TicketCreate


def test_tickets_file_loads():
    tickets = _load_tickets()
    assert len(tickets) >= 15


def test_search_by_keyword():
    results = search_tickets(query="timeout")
    assert len(results) > 0
    assert any("timeout" in t["title"].lower() or "timeout" in " ".join(t.get("tags", [])) for t in results)


def test_search_by_service():
    results = search_tickets(service="payment-api")
    assert all(t["service"] == "payment-api" for t in results)


def test_search_by_priority():
    results = search_tickets(priority="P1")
    assert all(t["priority"] == "P1" for t in results)
    assert len(results) >= 3


def test_search_by_status():
    results = search_tickets(status="Resolved")
    assert all(t["status"] == "Resolved" for t in results)


def test_get_existing_ticket():
    ticket = get_ticket("INC-1001")
    assert ticket is not None
    assert ticket["ticket_id"] == "INC-1001"
    assert "connection pool" in ticket["root_cause"].lower()


def test_get_nonexistent_ticket():
    ticket = get_ticket("INC-9999")
    assert ticket is None


def test_search_plural_incidents():
    results = search_tickets(query="incidents")
    assert len(results) >= 0  # should not crash on plural


def test_search_limit_respected():
    results = search_tickets(limit=3)
    assert len(results) <= 3


@pytest.mark.asyncio
async def test_ticket_tool_search():
    tool = TicketTool()
    results = await tool.search(query="payment timeout", limit=3)
    assert len(results) > 0
    assert results[0].ticket_id.startswith("INC-")


@pytest.mark.asyncio
async def test_ticket_tool_get():
    tool = TicketTool()
    ticket = await tool.get_ticket("INC-1001")
    assert ticket is not None
    assert ticket.priority == "P1"
