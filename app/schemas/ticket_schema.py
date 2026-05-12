from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class TicketCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: str
    priority: str = Field(default="P3", pattern="^P[1-4]$")
    service: Optional[str] = None


class TicketUpdate(BaseModel):
    status: Optional[str] = None
    priority: Optional[str] = Field(default=None, pattern="^P[1-4]$")
    root_cause: Optional[str] = None
    resolution: Optional[str] = None


class TicketResponse(BaseModel):
    ticket_id: str
    title: str
    description: str
    priority: str
    status: str
    service: Optional[str] = None
    root_cause: Optional[str] = None
    resolution: Optional[str] = None
    created_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None


class TicketListResponse(BaseModel):
    tickets: list[TicketResponse]
    total: int
