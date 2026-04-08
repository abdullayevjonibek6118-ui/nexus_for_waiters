# Architecture Guide

System architecture and component interaction for the Nexus AI platform.

---

## Table of Contents

- [System Overview](#system-overview)
- [Component Architecture](#component-architecture)
- [Data Flow](#data-flow)
- [Database Architecture](#database-architecture)
- [Multi-Tenancy & Data Isolation](#multi-tenancy--data-isolation)
- [State Machines](#state-machines)
- [External Integrations](#external-integrations)
- [Scheduler Architecture](#scheduler-architecture)
- [Error Handling](#error-handling)
- [Performance Considerations](#performance-considerations)

---

## System Overview

Nexus AI is a **Telegram bot-based SaaS platform** that connects event staffing agencies (companies/recruiters) with job seekers (candidates). The system operates as a multi-tenant application where each company has isolated data and dedicated communication channels.

### Key Actors

```
┌─────────────────────────────────────────────────────────────┐
│                         Actors                               │
├──────────────────┬──────────────────┬───────────────────────┤
│  Super Admin     │  Recruiter       │  Candidate            │
│  (SaaS Owner)    │  (Company Staff) │  (Job Seeker)         │
├──────────────────┼──────────────────┼───────────────────────┤
│ Manages          │ Creates events   │ Registers for events   │
│ companies        │ Publishes polls  │ Responds to invites    │
│ Extends subs     │ Reviews apps     │ Checks in on day       │
│ Monitors all     │ Assigns times    │ Receives payments      │
└──────────────────┴──────────────────┴───────────────────────┘
```

### Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Bot Framework** | python-telegram-bot 21+ | Telegram API interaction |
| **Database** | Supabase (PostgreSQL) | Data persistence, RLS |
| **Data Validation** | Pydantic 2+ | Type-safe models |
| **Scheduler** | APScheduler 3.10+ | Background tasks |
| **Sheets** | Google Sheets API | Collaborative spreadsheets |
| **Excel** | openpyxl | Offline reporting |

---

## Component Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Telegram Cloud                            │
│  (Bot API, Webhooks, User Messages)                         │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTPS (long polling)
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   main.py (Entry Point)                      │
├─────────────────────────────────────────────────────────────┤
│  • Application Builder (PTB)                                │
│  • PicklePersistence (conversation state)                   │
│  • Handler Registration (commands, callbacks, messages)     │
│  • APScheduler Initialization                               │
│  • Event Loop Management                                    │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   handlers/ (Interaction Layer)               │
├──────────────────┬──────────────────┬───────────────────────┤
│ start.py         │ admin_handler.py │ super_admin_handler.py│
│ event_handler.py │ candidate_handler│ onboarding_handler.py │
│ poll_handler.py  │ role_handler.py  │                       │
├──────────────────┴──────────────────┴───────────────────────┤
│  Responsibilities:                                           │
│  • Parse user input (commands, callbacks, text, contacts)   │
│  • Validate permissions (is_recruiter, is_super_admin)      │
│  • Route to appropriate service functions                   │
│  • Format and send responses to users                       │
│  • Manage ConversationHandler states                        │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   services/ (Business Logic)                  │
├──────────────────┬──────────────────┬───────────────────────┤
│ event_service.py │ candidate_svc.py │ company_service.py    │
│ recruiter_svc.py │ sheets_service.py│ excel_service.py      │
│ scheduler_svc.py │ audit_service.py │                       │
├──────────────────┴──────────────────┴───────────────────────┤
│  Responsibilities:                                           │
│  • Execute business logic                                   │
│  • Construct database queries                               │
│  • Call external APIs (Google Sheets)                       │
│  • Enforce data isolation (company_id filtering)            │
│  • Handle errors and raise custom exceptions                │
└────────────────────────┬────────────────────────────────────┘
                         │
          ┌──────────────┴──────────────┐
          ▼                             ▼
┌─────────────────────┐       ┌─────────────────────┐
│  Supabase Database  │       │  External Services  │
│  (Primary Storage)  │       │  (Google, Telegram) │
└─────────────────────┘       └─────────────────────┘
```

---

## Data Flow

### 1. Event Creation Flow

```
Recruiter                  Bot                        Services                  Database
   │                        │                            │                        │
   │── /create_event ──────>│                            │                        │
   │                        │── start conversation ─────>│                        │
   │<─ "Enter title" ──────│                            │                        │
   │                        │                            │                        │
   │── "Corporate Party" ──>│                            │                        │
   │                        │── save to user_data ──────>│                        │
   │<─ "Enter date" ───────│                            │                        │
   │                        │                            │                        │
   │── (9 steps total) ────>│                            │                        │
   │                        │                            │                        │
   │                        │── Event model ────────────>│ create_event()         │
   │                        │                            │── INSERT events ──────>│
   │                        │                            │<── event_id ───────────│
   │                        │<── Event object ──────────│                        │
   │<─ "Event created!" ───│                            │                        │
```

### 2. Candidate Registration Flow (Deep Linking)

```
Candidate                Telegram                 Bot                      Services            Database
   │                       │                       │                          │                   │
   │── Click "Register" ──>│                       │                          │                   │
   │   (deep link)         │                       │                          │                   │
   │                       │── /start event_123 ──>│                          │                   │
   │                       │                       │── start onboarding ─────>│                   │
   │<─ "Choose role" ──────│                       │                          │                   │
   │                       │                       │                          │                   │
   │── "Waiter" ──────────>│                       │                          │                   │
   │── (5 steps) ─────────>│                       │                          │                   │
   │                       │                       │                          │                   │
   │                       │                       │── Candidate profile ────>│ get_or_create()   │
   │                       │                       │                          │── UPSERT candidates │
   │                       │                       │                          │<── ok ─────────────│
   │                       │                       │                          │                   │
   │                       │                       │── Application ──────────>│ apply_for_event() │
   │                       │                       │                          │── INSERT event_cand│
   │                       │                       │                          │<── ok ─────────────│
   │                       │                       │                          │                   │
   │<─ "Application sent!" │                       │                          │                   │
```

### 3. Poll Publishing & Candidate Application Flow

```
Recruiter               Bot                     Services                Supabase           Telegram Group
   │                     │                         │                        │                    │
   │── /publish_poll ──>│                         │                        │                    │
   │                     │── get_event() ─────────>│                        │                    │
   │                     │<── Event object ────────│                        │                    │
   │                     │                         │                        │                    │
   │                     │── Build message ────────│                        │                    │
   │                     │   with inline button     │                        │                    │
   │                     │                         │                        │                    │
   │                     │── send_message() ────────────────────────────────────────────────────>│
   │                     │<── message_id ───────────────────────────────────────────────────────│
   │                     │                         │                        │                    │
   │                     │── save_poll_published_info()                     │                    │
   │                     │                         │── UPDATE events ──────>│                    │
   │                     │                         │   (chat_id, msg_id)    │                    │
   │                     │<── ok ──────────────────│                        │                    │
   │<─ "Published!" ────│                         │                        │                    │
   │                     │                         │                        │                    │
   │                     │                         │                        │                    │
   │                     │            Candidate clicks button               │                    │
   │                     │<─────────────────────────────────────────────────────────────────────│
   │                     │   (deep link: /start event_123)                  │                    │
   │                     │── Start onboarding ──────│                        │                    │
   │                     │   (see registration flow above)                  │                    │
```

### 4. Event Archiving Flow (with Channel Post Update)

```
Recruiter               Bot                     Services                Supabase           Telegram Channel
   │                     │                         │                        │                    │
   │── /close_event ───>│                         │                        │                    │
   │                     │── get_event() ─────────>│                        │                    │
   │                     │<── Event (with          │                        │                    │
   │                     │    channel_chat_id,      │                        │                    │
   │                     │    channel_message_id)   │                        │                    │
   │                     │                         │                        │                    │
   │                     │── update_event_status()─>│                        │                    │
   │                     │                         │── UPDATE status ──────>│                    │
   │                     │                         │   CLOSED               │                    │
   │                     │<── ok ──────────────────│                        │                    │
   │                     │                         │                        │                    │
   │                     │── edit_message_text() ──────────────────────────────────────────────>│
   │                     │   (add "🔴 ЗАКРЫТО",                                                  │
   │                     │    remove buttons)                                                    │
   │                     │<── ok (or error) ───────────────────────────────────────────────────│
   │                     │                         │                        │                    │
   │                     │── If media post, retry ─────────────────────────────────────────────>│
   │                     │   edit_message_caption()                                              │
   │                     │<── ok ──────────────────────────────────────────────────────────────│
   │                     │                         │                        │                    │
   │                     │── log_action() ─────────>│                        │                    │
   │                     │                         │── INSERT event_logs ──>│                    │
   │                     │<── ok ──────────────────│                        │                    │
   │                     │                         │                        │                    │
   │<─ "Event closed" ──│                         │                        │                    │
   │   (+ post status)   │                         │                        │                    │
```

---

## Database Architecture

### Entity Relationship Diagram

```
┌──────────────┐         ┌──────────────┐
│  companies   │◄────────│  recruiters  │
├──────────────┤         ├──────────────┤
│ id (UUID) PK│         │ user_id PK   │
│ name         │         │ company_id FK│
│ sub_until    │         │ first_name   │
│ monthly_fee  │         │ is_active    │
│ group_chat_id│         └──────────────┘
│ status       │
│ created_at   │
└──────┬───────┘
       │
       │ 1:N
       ▼
┌──────────────┐
│    events    │
├──────────────┤
│ event_id PK  │
│ company_id FK│
│ title        │
│ date         │─────────────────────┐
│ location     │                     │
│ payment      │                     │
│ max_cands    │                     │
│ status       │                     │
│ poll_id      │                     │ 1:N
│ sheet_url    │                     ▼
│ roles (JSON) │              ┌──────────────┐
│ times (JSON) │              │event_candidates│
│ channel_*    │              ├──────────────┤
│ created_by   │              │ id PK        │
│ created_at   │              │ event_id FK  │◄─── N:1
└──────────────┘              │ user_id FK   │─────┐
       ▲                      │ app_status   │     │
       │                      │ role         │     │
       │                      │ arrival_time │     │
       │                      │ depart_time  │     │
       │                      └──────┬───────┘     │
       │                             │              │
       │                             │ N:1          │ 1:N
       │                             ▼              │
       │                     ┌──────────────┐      │
       │                     │  candidates  │      │
       │                     ├──────────────┤      │
       └─────────────────────│ user_id PK   │◄─────┘
                             │ first_name   │
                             │ last_name    │
                             │ full_name    │
                             │ phone        │
                             │ gender       │
                             │ primary_role │
                             └──────────────┘

┌──────────────┐
│ event_logs   │
├──────────────┤
│ log_id PK    │
│ event_id FK  │
│ action       │
│ performed_by │
│ timestamp    │
│ details JSON │
└──────────────┘
```

### Key Relationships

| Relationship | Type | Description |
|-------------|------|-------------|
| `companies` → `recruiters` | 1:N | One company has many recruiters |
| `companies` → `events` | 1:N | One company owns many events |
| `events` → `event_candidates` | 1:N | One event has many applications |
| `candidates` → `event_candidates` | 1:N | One candidate applies to many events |
| `events` → `event_logs` | 1:N | One event has many log entries |

### Indexes

Performance-critical indexes:
- `events.status` — Filter active events
- `events.poll_id` — Lookup by poll ID
- `event_candidates.event_id` — Get applicants for event
- `event_candidates.user_id` — Get candidate's applications
- `event_logs.event_id`, `event_logs.timestamp` — Query recent logs

### Row Level Security (RLS)

RLS is enabled but bypassed by the bot using `service_role` key. RLS policies are defined for future API access control.

---

## Multi-Tenancy & Data Isolation

### Isolation Strategy

**Logical Isolation via `company_id`**: All recruiter-facing queries filter by `company_id` to ensure data separation.

### Enforcement Points

#### 1. Handler Level

Every recruiter command checks company ownership:

```python
# In handlers/admin_handler.py
async def is_recruiter(user_id: int) -> bool:
    if user_id == settings.super_admin_id:
        return True
    return await recruiter_service.is_recruiter(user_id)

# In each command handler
if update.effective_user.id != settings.super_admin_id:
    recruiter = await recruiter_service.get_recruiter(update.effective_user.id)
    if not recruiter or str(recruiter.get("company_id")) != str(event.company_id):
        await update.effective_message.reply_text("⛔ Ошибка доступа: Это мероприятие принадлежит другой компании.")
        return
```

#### 2. Service Level

Service functions accept optional `company_id` for filtering:

```python
async def get_active_events(company_id: Optional[str] = None) -> List[Event]:
    query = db.table("events").select("*").neq("status", EventStatus.CLOSED.value)
    if company_id:
        query = query.eq("company_id", company_id)  # Isolation enforced here
    result = query.execute()
    return [Event(**row) for row in result.data]
```

#### 3. Database Level

- Foreign key constraints ensure referential integrity
- `ON DELETE CASCADE` ensures cleanup when companies/events are deleted
- RLS policies defined (currently bypassed by service_role key)

### Super Admin Exemption

Super Admin (`SUPER_ADMIN_ID`) bypasses all isolation checks and can access all companies, events, and logs.

---

## State Machines

### 1. Application Status Machine

**Location**: `models/event_candidate.py`

Enforces valid transitions in candidate application lifecycle.

```
PENDING ──→ ACCEPTED ──→ SCHEDULED ──→ INVITED ──→ CONFIRMED ──→ CHECKED_IN
   │           │             │             │             │
   │           ├──→ REJECTED ├──→ REJECTED  ├──→ DECLINED  ├──→ DECLINED
   │           └──→ INVITED
   └──→ REJECTED
```

**Implementation:**

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

def can_transition(current: ApplicationStatus, next_status: ApplicationStatus) -> bool:
    return next_status in ALLOWED_TRANSITIONS.get(current, set())
```

**Usage in service:**

```python
async def transition_application(event_id, user_id, target_status):
    current = get_current_status(event_id, user_id)
    if not can_transition(current, target_status):
        raise InvalidStatusTransitionError(current, target_status)
    # Update status in DB
```

### 2. ConversationHandler States

Multi-step conversations use PTB's ConversationHandler:

**Event Creation (9 states):**
```
E_TITLE → E_DATE → E_LOC → E_PAYMENT → E_MAX → E_GENDERS → E_ROLES → E_TIMES → E_END_TIME → END
```

**Candidate Onboarding (7 states):**
```
WAIT_REG_START → CHOOSE_ROLE → SHARE_PHONE → INPUT_NAME → CHOOSE_GENDER → CHOOSE_TIME → CONFIRM_DATA → END
```

**State Persistence:**
- `PicklePersistence` stores conversation state across bot restarts
- `persistent=False` for event creation (transient)
- `persistent=True` for onboarding (survives restarts)

---

## External Integrations

### 1. Google Sheets Integration

**File**: `services/sheets_service.py`

**Flow:**
```
create_event_sheet()
    │
    ├─→ asyncio.to_thread(_create_spreadsheet_sync())
    │       │
    │       ├─→ Google Sheets API: Create spreadsheet
    │       ├─→ Apply formatting (bold headers, auto-resize columns)
    │       ├─→ Populate candidate rows
    │       └─→ Set sharing permissions
    │
    └─→ Return public URL
```

**Blocking Call Handling:**
Google API calls run in thread pool via `asyncio.to_thread()` to avoid blocking the event loop.

**Credentials:**
Service account JSON at `credentials/google_service_account.json` (configured via `GOOGLE_CREDENTIALS_FILE` env var).

### 2. Excel Export

**File**: `services/excel_service.py`

**Flow:**
```
generate_event_xlsx()
    │
    ├─→ Create Workbook with openpyxl
    ├─→ Add headers (Name, Gender, Phone, TG Username, Arrival, Departure, Hours, Rate, Payable)
    ├─→ Add candidate rows with Excel formulas
    │   (e.g., =IF(G2>0, G2*H2, 0) for payable calculation)
    ├─→ Save to temporary file
    └─→ Return file path (caller deletes after sending)
```

**Temporary File Management:**
```python
try:
    filepath = await asyncio.to_thread(excel_service.generate_event_xlsx, ...)
    with open(filepath, "rb") as f:
        await context.bot.send_document(chat_id=..., document=f, ...)
finally:
    if os.path.exists(filepath):
        os.remove(filepath)  # Guaranteed cleanup
```

### 3. Telegram Bot API

**Communication Method:** Long polling (not webhooks)

**Timeouts:**
- Connect: 30s
- Read: 60s
- Write: 60s

**Message Types Used:**
- Text messages (commands, responses)
- Inline keyboards (callback buttons)
- Reply keyboards (persistent menus)
- Documents (Excel file sends)
- Contacts (phone number sharing)

**Rate Limiting:**
Telegram API limits: 30 messages/second for bots. Mass broadcasts (`/announce`) send sequentially with error tracking.

---

## Scheduler Architecture

**File**: `services/scheduler_service.py`

### Singleton Pattern

```python
_scheduler: AsyncIOScheduler | None = None

def get_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is None:
        tz = pytz.timezone(settings.timezone)
        _scheduler = AsyncIOScheduler(
            jobstores={"default": MemoryJobStore()},
            timezone=tz,
        )
    return _scheduler

async def get_scheduler_async() -> AsyncIOScheduler:
    scheduler = get_scheduler()
    if not scheduler.running:
        scheduler.start()
    return scheduler
```

### Job Types

#### 1. One-Shot: Payment Reminder

**Trigger:** Scheduled at event creation + 14 days

**Action:** Send message to all admin IDs with `/payment_confirmed` command

**Cancellation:** When payment is confirmed or event is closed

**Job ID Format:** `payment_reminder_{event_id}`

#### 2. Cron: Daily Event Reminders

**Trigger:** Daily at 18:00 (Asia/Tashkent)

**Action:**
1. Find all active events happening **tomorrow**
2. Check company subscription status
3. Send reminder to all `CONFIRMED` candidates
4. Include event details and arrival time

**Job ID:** `daily_tomorrow_reminders`

### Startup Initialization

```python
# In main.py
async def on_startup(app):
    await get_scheduler_async()
    from services.scheduler_service import schedule_daily_reminders
    await schedule_daily_reminders(app.bot)
```

---

## Error Handling

### Exception Hierarchy

```
NexusError (base)
├── DatabaseError          — Supabase query failures
├── EventNotFoundError     — Event lookup failures
├── AccessDeniedError      — Permission violations
└── ValidationError        — Input validation failures
```

### Error Handling Strategy

#### Service Layer

```python
async def do_something(event_id: str):
    try:
        db = get_db()
        result = db.table("events").select("*").eq("event_id", event_id).execute()
        if not result.data:
            raise EventNotFoundError(f"Event {event_id} not found")
        return result.data[0]
    except EventNotFoundError:
        raise  # Re-raise expected exceptions
    except Exception as e:
        logger.error(f"do_something error: {e}")
        raise DatabaseError(f"Database error: {e}")  # Wrap unexpected errors
```

#### Handler Layer

```python
async def handler_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        event = await event_service.get_event(event_id)
    except EventNotFoundError:
        await update.message.reply_text("❌ Мероприятие не найдено.")
        return
    except DatabaseError as e:
        logger.error(f"DB error: {e}")
        await update.message.reply_text("⚠️ Ошибка базы данных. Попробуйте позже.")
        return

    # Continue with happy path
```

### User-Facing Error Messages

| Error Type | User Message | Log Level |
|-----------|-------------|-----------|
| Not found | "❌ Мероприятие не найдено." | WARNING |
| No permissions | "⛔ У вас нет прав." | INFO |
| Database error | "⚠️ Ошибка базы данных." | ERROR |
| External API error | "❌ Не удалось создать Google Sheet." | ERROR |
| Validation error | "❌ Неверный формат. Используйте HH:MM" | WARNING |

---

## Performance Considerations

### N+1 Query Optimization

**Problem:** Fetching applicants with individual profile queries:
```python
# BAD: N+1 queries
applicants = await get_applicants(event_id)
for app in applicants:
    profile = await get_candidate_profile(app["user_id"])  # 100 queries for 100 applicants
```

**Solution:** Single join query:
```python
# GOOD: 1 query
result = db.table("event_candidates").select(
    "*, candidates(first_name,last_name,phone,gender,primary_role)"
).eq("event_id", event_id).execute()
```

**Implementation:** `candidate_service.get_applicants()` uses join query, returns nested dicts.

### Caching

**Conversation State:** `context.user_data` caches:
- Event lists for Reply keyboard matching
- Candidate card data during review sessions
- Time assignment state during `/set_times`

**Persistence:** `PicklePersistence` stores conversation state to `bot_persistence.pickle` for restart recovery.

### Async I/O

All database and external API calls are async or wrapped:
```python
# Thread pool for blocking operations
await asyncio.to_thread(sheets_service.create_event_sheet, ...)
await asyncio.to_thread(excel_service.generate_event_xlsx, ...)
```

### Temporary File Cleanup

Excel files created in `/export_excel` are guaranteed deleted via `finally` block, even on send failures.

---

## Security Considerations

### Data Isolation

- Every recruiter query filters by `company_id`
- Super Admin bypasses isolation
- No cross-company data leakage

### Sensitive Data

- Bot token, Supabase key in `.env` (gitignored)
- Google credentials in `credentials/` (gitignored)
- Service account JSON never logged or exposed

### Input Validation

- Time formats validated with regex
- Date formats parsed with fallbacks
- Max candidates bounded (1-100)
- SQL injection prevented by Supabase ORM

### Rate Limiting

- Telegram API: 30 msg/sec limit respected
- Mass broadcasts send sequentially with error tracking
- No explicit user rate limiting (relying on Telegram's built-in limits)

---

[← Back to README](README.md) | [Contributing →](CONTRIBUTING.md)
