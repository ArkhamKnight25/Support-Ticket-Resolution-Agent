from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from app.schemas.ticket_schema import TicketCreate, TicketResponse, TicketListResponse, TicketUpdate
from app.tools.ticket_tool import TicketTool
from app.dependencies import require_api_key

router = APIRouter()


def get_ticket_tool() -> TicketTool:
    return TicketTool()


@router.post("/", response_model=TicketResponse)
async def create_ticket(
    ticket: TicketCreate,
    tool: TicketTool = Depends(get_ticket_tool),
    _: None = Depends(require_api_key),
):
    result = await tool.create_ticket(ticket)
    return result


@router.get("/", response_model=TicketListResponse)
async def list_tickets(
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    limit: int = Query(20, le=100),
    tool: TicketTool = Depends(get_ticket_tool),
    _: None = Depends(require_api_key),
):
    tickets = await tool.list_tickets(status=status, priority=priority, limit=limit)
    return TicketListResponse(tickets=tickets, total=len(tickets))


@router.get("/{ticket_id}", response_model=TicketResponse)
async def get_ticket(
    ticket_id: str,
    tool: TicketTool = Depends(get_ticket_tool),
    _: None = Depends(require_api_key),
):
    ticket = await tool.get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found.")
    return ticket


@router.patch("/{ticket_id}", response_model=TicketResponse)
async def update_ticket(
    ticket_id: str,
    update: TicketUpdate,
    tool: TicketTool = Depends(get_ticket_tool),
    _: None = Depends(require_api_key),
):
    ticket = await tool.update_ticket(ticket_id, update)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found.")
    return ticket
