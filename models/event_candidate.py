"""Модели данных для связки Event <-> Candidate."""
from typing import Optional
from pydantic import BaseModel
from models.candidate import VoteStatus


class EventCandidate(BaseModel):
    event_id: str
    user_id: int
    vote_status: Optional[VoteStatus] = None
    selected: bool = False
    arrival_time: Optional[str] = None    # HH:MM (24h)
    departure_time: Optional[str] = None  # HH:MM (24h)
    is_checked_in: bool = False
    is_checkin_confirmed: bool = False
    confirmed: bool = False
