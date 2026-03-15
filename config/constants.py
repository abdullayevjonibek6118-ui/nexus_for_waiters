"""
Nexus AI — Constants
"""

class EventStatus:
    DRAFT = "Draft"
    ACTIVE = "Active"
    POLL_PUBLISHED = "Poll_Published"
    CANDIDATES_SELECTED = "Candidates_Selected"
    NOTIFIED = "Notified"
    SHEET_GENERATED = "Sheet_Generated"
    PAYMENT_PENDING = "Payment_Pending"
    COMPLETED = "Completed"
    CLOSED = "Closed"
    CANCELLED = "Cancelled"

class CandidateRole:
    WAITER = "Официант"
    HOSTESS = "Хостес"
    BARMAN = "Бармен"
    KITCHEN = "Повар/Кухня"
    CLEANER = "Уборщик"

class VoteStatus:
    YES = "yes"
    MAYBE = "maybe"
    NO = "no"

class Gender:
    MALE = "Male"
    FEMALE = "Female"
