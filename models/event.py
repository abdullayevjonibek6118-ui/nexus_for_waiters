"""Модели данных для мероприятий."""
from enum import Enum
from datetime import date
from typing import Optional
from pydantic import BaseModel


class EventStatus(str, Enum):
    DRAFT = "Draft"
    POLL_PUBLISHED = "Poll_Published"
    RECRUITING = "Recruiting"
    SELECTION_COMPLETED = "Selection_Completed"
    TIMES_ASSIGNED = "Times_Assigned"
    SHEET_GENERATED = "Sheet_Generated"
    CANDIDATES_CONFIRMED = "Candidates_Confirmed"
    COMPLETED = "Completed"
    PAYMENT_PENDING = "Payment_Pending"
    CLOSED = "Closed"
    CANCELLED = "Cancelled"


class Event(BaseModel):
    event_id: Optional[str] = None
    company_id: Optional[str] = None
    title: str
    date: str                          # ISO date string: YYYY-MM-DD
    location: str
    payment: Optional[str] = None
    max_candidates: int = 10
    status: EventStatus = EventStatus.DRAFT
    poll_id: Optional[str] = None
    sheet_url: Optional[str] = None
    required_roles: list[str] = []
    arrival_times: list[str] = []
    required_men: int = 0
    required_women: int = 0
    created_by: Optional[int] = None   # Telegram user_id рекрутера
