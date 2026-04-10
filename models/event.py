"""Модели данных для мероприятий."""
from enum import Enum
from datetime import date
from typing import Optional
from pydantic import BaseModel


from utils.constants import EventStatus


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
    end_time: Optional[str] = None
    required_men: int = 0
    required_women: int = 0
    channel_chat_id: Optional[str] = None
    channel_message_id: Optional[str] = None
    created_by: Optional[int] = None   # Telegram user_id рекрутера
    created_at: Optional[str] = None   # ISO datetime string
