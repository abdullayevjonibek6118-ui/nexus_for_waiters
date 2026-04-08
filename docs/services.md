# Services Documentation

Business logic layer for the Nexus AI platform. All services interact with Supabase, external APIs (Google Sheets), and the scheduler.

---

## Table of Contents

- [Event Service](#event-service)
- [Candidate Service](#candidate-service)
- [Company Service](#company-service)
- [Recruiter Service](#recruiter-service)
- [Sheets Service](#sheets-service)
- [Excel Service](#excel-service)
- [Scheduler Service](#scheduler-service)
- [Audit Service](#audit-service)

---

## Event Service

**File**: `services/event_service.py`

Handles event CRUD operations and status management.

### Functions

#### `create_event(event: Event) -> Event`

Creates a new event in Supabase.

**Parameters:**
- `event`: Pydantic Event model with all fields populated

**Returns:** Event with populated `event_id`

**Raises:** `DatabaseError` if insert fails

**Example:**
```python
from services import event_service
from models.event import Event

event = Event(
    title="Corporate Party",
    date="2026-05-01",
    location="Moscow",
    max_candidates=15,
    company_id="uuid",
    created_by=123456
)
saved_event = await event_service.create_event(event)
```

---

#### `get_event(event_id: str) -> Event`

Retrieves an event by ID.

**Raises:** `EventNotFoundError` if event doesn't exist

---

#### `get_active_events(company_id: Optional[str] = None) -> List[Event]`

Returns all non-closed events. If `company_id` is provided, filters by company (data isolation).

---

#### `update_event_status(event_id: str, status: EventStatus) -> bool`

Updates the event's status field.

---

#### `save_poll_published_info(event_id: str, poll_id: str, chat_id: str, message_id: str) -> bool`

**Important**: Updates 4 fields in one query:
- `poll_id`
- `status` → `POLL_PUBLISHED`
- `channel_chat_id`
- `channel_message_id`

Called from `handlers/poll_handler.py` after successfully publishing a hiring announcement.

---

#### `save_sheet_url(event_id: str, sheet_url: str) -> bool`

Updates `sheet_url` and sets status to `SHEET_GENERATED`.

---

#### `get_event_by_poll_id(poll_id: str) -> Optional[Event]`

Finds event by its poll_id (used for poll answer handling).

---

## Candidate Service

**File**: `services/candidate_service.py`

Manages candidate profiles and event applications.

### Functions

#### `apply_for_event(event_id, user_id, role, arrival_time, departure_time) -> bool`

Registers a candidate for an event. Uses `upsert` to handle duplicate registrations.

**Sets:**
- `application_status` → `PENDING`
- `vote_status` → `YES` (legacy compatibility)

---

#### `transition_application(event_id, user_id, target_status: ApplicationStatus) -> bool`

Changes application status with state machine validation.

**Raises:**
- `CandidateNotFoundError` if application doesn't exist
- `InvalidStatusTransitionError` if transition is invalid

**Side Effects:**
- Sets `selected=True` when transitioning to `ACCEPTED`
- Sets `confirmed=True` when transitioning to `CONFIRMED`
- Sets `is_checked_in=True` and `is_checkin_confirmed=True` for `CHECKED_IN`

**Example:**
```python
from services.candidate_service import transition_application
from models.event_candidate import ApplicationStatus

# Accept a candidate
await transition_application(event_id, user_id, ApplicationStatus.ACCEPTED)

# Reject a candidate
await transition_application(event_id, user_id, ApplicationStatus.REJECTED)
```

---

#### `get_or_create_candidate(user_id, first_name, last_name, username) -> Candidate`

Retrieves or creates a candidate profile. Updates existing profiles with latest Telegram info.

---

#### `update_phone_number(user_id, phone) -> bool`

Updates candidate's phone number.

---

#### `update_candidate_gender(user_id, gender) -> bool`

Updates candidate's gender (`"Male"` or `"Female"`).

---

#### `update_candidate_full_name(user_id, full_name) -> bool`

Updates candidate's legal name (passport name).

---

#### `get_applicants(event_id, status: Optional[ApplicationStatus] = None) -> List[dict]`

Returns applicants for an event with candidate profile data joined in one query (N+1 fix).

**Parameters:**
- `event_id`: Event UUID
- `status`: Filter by application status (optional)

**Returns:** List of dicts with nested `candidates` object:
```python
{
    "user_id": 123,
    "application_status": "PENDING",
    "role": "Waiter",
    "arrival_time": "08:00",
    "candidates": {
        "first_name": "John",
        "last_name": "Doe",
        "phone_number": "+79001234567",
        "telegram_username": "johndoe",
        "gender": "Male"
    }
}
```

---

#### `get_selected_candidates(event_id) -> list`

Returns candidates with `ACCEPTED` status (legacy compatibility wrapper).

---

#### `get_company_applicants(company_id) -> list`

Returns all applicants across all events for a company. Joins `event_candidates`, `candidates`, and `events` tables.

---

#### `set_arrival_departure(event_id, user_id, arrival, departure) -> bool`

Sets candidate's shift times.

---

#### `select_candidate(event_id, user_id, selected: bool) -> bool`

Accepts or rejects a candidate via `transition_application`. Falls back to direct DB update if transition fails.

---

#### `confirm_checkin(event_id, user_id) -> bool`

Marks `is_checkin_confirmed=True` (recruiter confirmed candidate's arrival).

---

#### `get_candidate_profile(user_id) -> Optional[Candidate]`

Returns candidate profile by user ID.

---

#### `get_event_candidate(event_id, user_id) -> dict`

Returns raw application record for a specific candidate-event pair.

---

## Company Service

**File**: `services/company_service.py`

Manages SaaS tenant companies and subscriptions.

### Functions

#### `create_company(name, monthly_fee) -> dict`

Creates a new company with `subscription_until` set to `NULL` (inactive).

---

#### `get_company(company_id) -> dict`

Retrieves company details.

---

#### `list_companies() -> list`

Returns all companies.

---

#### `update_subscription(company_id, until_date: datetime) -> bool`

Updates `subscription_until` field.

---

#### `check_subscription(company_id) -> bool`

Checks if company's subscription is active.

**Returns:** `True` if `subscription_until > now()`, else `False`

**Usage:**
```python
from services import company_service

if not await company_service.check_subscription(company_id):
    logger.warning("Subscription expired")
    # Block recruiter actions
```

---

## Recruiter Service

**File**: `services/recruiter_service.py`

Manages recruiter-company relationships.

### Functions

#### `add_recruiter(user_id, company_id) -> dict`

Adds a recruiter to a company.

---

#### `get_recruiter(user_id) -> dict`

Returns recruiter profile with nested `companies` object (via join).

---

#### `is_recruiter(user_id) -> bool`

Checks if user is an active recruiter.

---

#### `list_company_recruiters(company_id) -> list`

Returns all recruiters for a company.

---

## Sheets Service

**File**: `services/sheets_service.py`

Google Sheets integration for candidate reporting.

### Functions

#### `create_event_sheet(event_title, event_date, event_location, candidates) -> str`

Creates a Google Spreadsheet with candidate data.

**Features:**
- Auto-generates spreadsheet with headers
- Populates candidate rows
- Applies bold header styling
- Auto-resizes columns
- Returns public URL

**Called from:** `/create_sheet` command

**Note:** Runs in thread via `asyncio.to_thread()` to avoid blocking event loop.

---

## Excel Service

**File**: `services/excel_service.py`

Generates `.xlsx` files for offline reporting.

### Functions

#### `generate_event_xlsx(event_title, event_date, event_location, candidates) -> str`

Creates an Excel workbook with:
- Headers: Name, Gender, Phone, TG Username, Arrival, Departure, Hours Worked, Rate, Payable
- Auto-calculated Excel formulas for payment calculations
- Sanitized data (control characters stripped)

**Returns:** Path to temporary `.xlsx` file (caller must delete after use)

---

#### `generate_company_report_xlsx(company_name, candidates) -> str`

Creates cross-event report for all candidates in a company.

---

#### `sanitize_for_excel(text) -> str`

Strips control characters that break Excel formulas.

---

## Scheduler Service

**File**: `services/scheduler_service.py`

APScheduler integration for background tasks.

### Singleton Pattern

```python
from services.scheduler_service import get_scheduler, get_scheduler_async

scheduler = await get_scheduler_async()  # Initializes and starts scheduler
```

### Functions

#### `schedule_payment_reminder(event_id, event_title, bot, admin_ids, days=14) -> str`

Schedules a one-shot reminder to notify admins after N days.

**Returns:** `job_id` (format: `payment_reminder_{event_id}`)

**Triggers:** Sends message to each admin with `/payment_confirmed` command.

---

#### `cancel_reminder(job_id) -> bool`

Cancels a scheduled payment reminder.

---

#### `schedule_daily_reminders(bot)`

Adds a cron job that runs daily at 18:00 (Asia/Tashkent timezone).

**Behavior:**
1. Finds all active events happening **tomorrow**
2. Checks company subscription status
3. Sends reminder to all `CONFIRMED` candidates
4. Includes event details and arrival time

**Called from:** `main.py` on bot startup

---

## Audit Service

**File**: `services/audit_service.py`

Event logging for compliance and debugging.

### Functions

#### `log_action(event_id, action, performed_by, details={}) -> bool`

Inserts a log entry into `event_logs` table.

**Fields:**
- `log_id`: Auto-generated UUID
- `timestamp`: Current timestamp
- `details`: JSON-serializable dict (optional)

**Example:**
```python
from services import audit_service

await audit_service.log_action(
    event_id,
    "event_closed",
    user_id=123456,
    details={"reason": "Event completed"}
)
```

---

#### `get_event_logs(event_id, limit=15) -> list`

Returns last N log entries for an event (newest first).

---

## Service Dependencies

```
admin_handler.py
    ├── event_service
    ├── candidate_service
    ├── sheets_service
    ├── audit_service
    ├── scheduler_service
    ├── recruiter_service
    └── excel_service

candidate_handler.py
    ├── event_service
    ├── candidate_service
    └── audit_service

event_handler.py
    ├── event_service
    ├── recruiter_service
    ├── candidate_service
    └── audit_service

poll_handler.py
    ├── event_service
    ├── candidate_service
    ├── recruiter_service
    └── audit_service
```

---

[← Models](models.md) | [Handlers →](handlers.md)
