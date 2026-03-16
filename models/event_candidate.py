"""Модели данных для связки Event <-> Candidate."""
from typing import Optional
from pydantic import BaseModel
from utils.constants import VoteStatus, ApplicationStatus


# Разрешённые переходы между статусами заявки.
ALLOWED_TRANSITIONS: dict[ApplicationStatus, set[ApplicationStatus]] = {
    ApplicationStatus.PENDING:    {ApplicationStatus.ACCEPTED, ApplicationStatus.REJECTED},
    ApplicationStatus.ACCEPTED:   {ApplicationStatus.SCHEDULED, ApplicationStatus.REJECTED},
    ApplicationStatus.SCHEDULED:  {ApplicationStatus.INVITED, ApplicationStatus.REJECTED},
    ApplicationStatus.INVITED:    {ApplicationStatus.CONFIRMED, ApplicationStatus.DECLINED},
    ApplicationStatus.CONFIRMED:  {ApplicationStatus.CHECKED_IN, ApplicationStatus.DECLINED},
    ApplicationStatus.CHECKED_IN: set(),  # терминальный
    ApplicationStatus.REJECTED:   set(),  # терминальный
    ApplicationStatus.DECLINED:   set(),  # терминальный
}


def can_transition(current: ApplicationStatus, next_status: ApplicationStatus) -> bool:
    """Проверяет допустимость перехода между статусами заявки."""
    return next_status in ALLOWED_TRANSITIONS.get(current, set())


class EventCandidate(BaseModel):
    event_id: str
    user_id: int
    
    # Единый статус вместо разрозненных флагов
    application_status: ApplicationStatus = ApplicationStatus.PENDING
    
    # Данные, специфичные для конкретного ивента (роль на ЭТОМ ивенте)
    role: Optional[str] = None
    arrival_time: Optional[str] = None    # HH:MM (24h)
    departure_time: Optional[str] = None  # HH:MM (24h)
    
    # Старые поля (deprecated, для обратной совместимости)
    vote_status: Optional[VoteStatus] = None
    selected: bool = False
    confirmed: bool = False
    is_checked_in: bool = False
    is_checkin_confirmed: bool = False
