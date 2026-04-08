# Models Documentation

Data models for the Nexus AI platform using Pydantic for validation and type safety.

---

## Table of Contents

- [Event Model](#event-model)
- [Candidate Model](#candidate-model)
- [EventCandidate Model](#eventcandidate-model)
- [Application Status State Machine](#application-status-state-machine)

---

## Event Model

**File**: `models/event.py`

Pydantic model representing an event in the system.

### Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `event_id` | `Optional[str]` | `None` | UUID of the event (auto-generated) |
| `company_id` | `Optional[str]` | `None` | UUID of the owning company (multi-tenancy) |
| `title` | `str` | Required | Event name |
| `date` | `str` | Required | Event date in ISO format (YYYY-MM-DD) |
| `location` | `str` | Required | Event venue/address |
| `payment` | `Optional[str]` | `None` | Payment information (e.g., "4000 ₽") |
| `max_candidates` | `int` | `10` | Maximum number of candidates needed |
| `status` | `EventStatus` | `DRAFT` | Current event lifecycle status |
| `poll_id` | `Optional[str]` | `None` | Identifier for published hiring announcement |
| `sheet_url` | `Optional[str]` | `None` | Google Sheets URL for selected candidates |
| `required_roles` | `list[str]` | `[]` | List of required roles (e.g., ["Waiter", "Hostess"]) |
| `arrival_times` | `list[str]` | `[]` | Available shift start times (e.g., ["08:00", "09:00"]) |
| `end_time` | `Optional[str]` | `None` | Event end time (HH:MM) |
| `required_men` | `int` | `0` | Number of male candidates needed |
| `required_women` | `int` | `0` | Number of female candidates needed |
| `channel_chat_id` | `Optional[str]` | `None` | Telegram chat ID where poll was published |
| `channel_message_id` | `Optional[str]` | `None` | Telegram message ID of the published poll |
| `created_by` | `Optional[int]` | `None` | Telegram user ID of the recruiting creator |

### Usage Example

```python
from models.event import Event
from utils.constants import EventStatus

event = Event(
    title="Corporate Event",
    date="2026-04-15",
    location="Moscow, Red Street 1",
    payment="4000 ₽",
    max_candidates=10,
    required_roles=["Waiter", "Hostess"],
    arrival_times=["08:00", "09:00"],
    end_time="22:00",
    required_men=4,
    required_women=6,
    company_id="uuid-here",
    created_by=123456789
)
```

---

## Candidate Model

**File**: `models/candidate.py`

Pydantic model representing a candidate's global profile.

### Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `user_id` | `int` | Required | Telegram user ID (primary key) |
| `first_name` | `str` | Required | First name from Telegram |
| `last_name` | `str` | `''` | Last name from Telegram |
| `full_name` | `str` | `''` | Full legal name (passport name) |
| `primary_role` | `str` | `''` | Candidate's main role (e.g., "Waiter") |
| `phone_number` | `str` | `''` | Contact phone number |
| `telegram_username` | `str` | `''` | Telegram username |
| `gender` | `str` | `''` | Gender: `"Male"` or `"Female"` |
| `has_messaged_bot` | `bool` | `False` | Whether candidate has interacted with bot |

### Usage Example

```python
from models.candidate import Candidate

candidate = Candidate(
    user_id=987654321,
    first_name="John",
    last_name="Doe",
    full_name="John Michael Doe",
    phone_number="+79001234567",
    telegram_username="johndoe",
    gender="Male",
    primary_role="Waiter"
)
```

---

## EventCandidate Model

**File**: `models/event_candidate.py`

Pydantic model representing a candidate's application for a specific event.

### Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `event_id` | `str` | Required | UUID of the event |
| `user_id` | `int` | Required | Telegram user ID of candidate |
| `application_status` | `ApplicationStatus` | `PENDING` | Current application status |
| `role` | `Optional[str]` | `None` | Role for THIS event (may differ from primary_role) |
| `arrival_time` | `Optional[str]` | `None` | Assigned arrival time (HH:MM) |
| `departure_time` | `Optional[str]` | `None` | Assigned departure time (HH:MM) |
| `vote_status` | `Optional[VoteStatus]` | `None` | **Deprecated**: Legacy poll vote |
| `selected` | `bool` | `False` | **Deprecated**: Use `application_status` |
| `confirmed` | `bool` | `False` | **Deprecated**: Use `application_status` |
| `is_checked_in` | `bool` | `False` | **Deprecated**: Use `application_status` |
| `is_checkin_confirmed` | `bool` | `False` | **Deprecated**: Use `application_status` |

### Usage Example

```python
from models.event_candidate import EventCandidate, ApplicationStatus

application = EventCandidate(
    event_id="event-uuid",
    user_id=987654321,
    application_status=ApplicationStatus.PENDING,
    role="Waiter",
    arrival_time="08:00",
    departure_time="20:00"
)
```

---

## Application Status State Machine

**File**: `models/event_candidate.py`

The application lifecycle is enforced through a state machine that prevents invalid status transitions.

### Allowed Transitions

```python
ALLOWED_TRANSITIONS = {
    ApplicationStatus.PENDING:    {ACCEPTED, REJECTED},
    ApplicationStatus.ACCEPTED:   {SCHEDULED, INVITED, REJECTED},
    ApplicationStatus.SCHEDULED:  {INVITED, REJECTED},
    ApplicationStatus.INVITED:    {CONFIRMED, DECLINED},
    ApplicationStatus.CONFIRMED:  {CHECKED_IN, DECLINED},
    ApplicationStatus.CHECKED_IN: set(),  # Terminal
    ApplicationStatus.REJECTED:   set(),  # Terminal
    ApplicationStatus.DECLINED:   set(),  # Terminal
}
```

### Transition Functions

#### `can_transition(current: ApplicationStatus, next_status: ApplicationStatus) -> bool`

Validates whether a transition is allowed.

```python
from models.event_candidate import can_transition, ApplicationStatus

# Valid transition
can_transition(ApplicationStatus.PENDING, ApplicationStatus.ACCEPTED)  # True

# Invalid transition
can_transition(ApplicationStatus.CHECKED_IN, ApplicationStatus.ACCEPTED)  # False
```

### Status Meanings

| Status | Meaning |
|--------|---------|
| `PENDING` | Candidate applied, awaiting review |
| `ACCEPTED` | Recruiter approved the application |
| `SCHEDULED` | Time assigned to candidate |
| `INVITED` | Invitation sent to candidate |
| `CONFIRMED` | Candidate accepted invitation |
| `CHECKED_IN` | Candidate arrived at event |
| `REJECTED` | Recruiter declined application |
| `DECLINED` | Candidate declined invitation |

### Legacy Support

The model includes deprecated fields (`vote_status`, `selected`, `confirmed`, `is_checked_in`, `is_checkin_confirmed`) for backward compatibility with older versions. New code should use `application_status` exclusively.

---

## Related Services

- **`services/event_service.py`** — Event CRUD operations
- **`services/candidate_service.py`** — Candidate profile and application management
- **`services/recruiter_service.py`** — Recruiter-company relationships

---

[← Back to README](../README.md) | [Services →](services.md)
