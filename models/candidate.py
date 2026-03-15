"""Модели данных для кандидатов."""
from enum import Enum
from typing import Optional
from pydantic import BaseModel


from utils.constants import VoteStatus


class Candidate(BaseModel):
    user_id: int                          # Telegram user_id (PK)
    first_name: str
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    primary_role: Optional[str] = None
    phone_number: Optional[str] = None
    telegram_username: Optional[str] = None
    gender: Optional[str] = None           # 'Male' or 'Female'
    has_messaged_bot: bool = False
