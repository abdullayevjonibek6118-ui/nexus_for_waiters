"""
Nexus AI — Constants
"""
from enum import Enum

class EventStatus(str, Enum):
    DRAFT = "Draft"
    ACTIVE = "Active"
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

class CandidateRole(str, Enum):
    WAITER = "Официант"
    HOSTESS = "Хостес"
    BARMAN = "Бармен"
    KITCHEN = "Повар/Кухня"
    CLEANER = "Уборщик"

class VoteStatus(str, Enum):
    YES = "yes"
    MAYBE = "maybe"
    NO = "no"

class ApplicationStatus(str, Enum):
    """Жизненный цикл заявки кандидата."""
    PENDING = "pending"          # Заявка подана, ждёт решения
    ACCEPTED = "accepted"        # Принят рекрутером
    SCHEDULED = "scheduled"      # Время назначено
    INVITED = "invited"          # Приглашение отправлено
    CONFIRMED = "confirmed"      # Подтвердил участие
    CHECKED_IN = "checked_in"    # На месте
    REJECTED = "rejected"        # Отклонен рекрутером
    DECLINED = "declined"        # Сам отказался

class Gender(str, Enum):
    MALE = "Male"
    FEMALE = "Female"
