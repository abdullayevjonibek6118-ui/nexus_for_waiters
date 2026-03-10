"""Модели данных для кандидатов."""
from enum import Enum
from typing import Optional
from pydantic import BaseModel


class VoteStatus(str, Enum):
    YES = "yes"
    NO = "no"
    MAYBE = "maybe"


class Candidate(BaseModel):
    user_id: int                          # Telegram user_id (PK)
    first_name: str
    last_name: Optional[str] = None
    phone_number: Optional[str] = None
    telegram_username: Optional[str] = None
    gender: Optional[str] = None           # 'Male' or 'Female'
    has_messaged_bot: bool = False
