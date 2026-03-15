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

class Gender(str, Enum):
    MALE = "Male"
    FEMALE = "Female"
