# Utils Documentation

Utility modules providing constants, keyboard builders, validators, and custom exceptions.

---

## Table of Contents

- [Constants (Enums)](#constants-enums)
- [Keyboards](#keyboards)
- [Validators](#validators)
- [Exceptions](#exceptions)

---

## Constants (Enums)

**File**: `utils/constants.py`

### EventStatus

Event lifecycle statuses.

| Status | Value | Meaning |
|--------|-------|---------|
| `DRAFT` | `Draft` | Event being created |
| `ACTIVE` | `Active` | Event saved, ready for polling |
| `POLL_PUBLISHED` | `Poll Published` | Hiring announcement posted to group |
| `RECRUITING` | `Recruiting` | Accepting candidate applications |
| `SELECTION_COMPLETED` | `Selection Completed` | Poll closed, reviewing candidates |
| `TIMES_ASSIGNED` | `Times Assigned` | Shift times set for candidates |
| `SHEET_GENERATED` | `Sheet Generated` | Google Sheet created |
| `CANDIDATES_CONFIRMED` | `Candidates Confirmed` | Candidates accepted invitations |
| `COMPLETED` | `Completed` | Event finished |
| `PAYMENT_PENDING` | `Payment Pending` | Awaiting payment confirmation |
| `CLOSED` | `Closed` | Event archived |

**Usage:**
```python
from utils.constants import EventStatus

await event_service.update_event_status(event_id, EventStatus.POLL_PUBLISHED)
```

---

### ApplicationStatus

Candidate application lifecycle (state machine enforced).

| Status | Value | Meaning |
|--------|-------|---------|
| `PENDING` | `Pending` | Applied, awaiting review |
| `ACCEPTED` | `Accepted` | Approved by recruiter |
| `SCHEDULED` | `Scheduled` | Time assigned |
| `INVITED` | `Invited` | Invitation sent |
| `CONFIRMED` | `Confirmed` | Candidate accepted invitation |
| `CHECKED_IN` | `Checked In` | Arrived at event |
| `REJECTED` | `Rejected` | Declined by recruiter |
| `DECLINED` | `Declined` | Candidate declined |

---

### CandidateRole

Available roles for event staffing.

| Role | Value |
|------|-------|
| `WAITER` | `Waiter` |
| `HOSTESS` | `Hostess` |
| `BARMAN` | `Barman` |
| `KITCHEN` | `Kitchen` |
| `CLEANER` | `Cleaner` |

**Note:** Events can define custom roles beyond this enum (e.g., "Promoter", "Registrar").

---

### VoteStatus

**Deprecated**: Legacy poll voting system.

| Status | Value |
|--------|-------|
| `YES` | `yes` |
| `MAYBE` | `maybe` |
| `NO` | `no` |

Still used in `apply_for_event()` for backward compatibility.

---

### Gender

| Value | Meaning |
|-------|---------|
| `MALE` | Male |
| `FEMALE` | Female |

---

## Keyboards

**File**: `utils/keyboards.py`

Builds Reply keyboards (persistent bottom buttons) and Inline keyboards (message-embedded buttons).

### Reply Keyboards

Persistent buttons that remain visible until replaced.

#### `get_recruiter_dashboard_keyboard()`

Main recruiter menu.
```
[🆕 Создать мероприятие] [📋 Мои мероприятия]
[📊 Отчеты]              [❓ Помощь]
```

#### `get_events_list_reply_keyboard(events)`

Dynamic list of active events.
```
[📅 2026-04-15 | Corporate Party]
[📅 2026-04-20 | Wedding Event]
[📅 2026-04-25 | Conference]
```

#### `get_event_action_reply_keyboard(event_title)`

Event management actions.
```
[📢 Опубликовать] [👥 Карточки]
[✉️ Уведомить]    [📄 Экспорт Excel]
[⏰ Назначить время] [🤖 Автоотбор]
[📊 Логи]         [❌ Архивировать]
[⬅️ К списку]
```

#### `get_onboarding_role_reply_keyboard(roles)`

Dynamic role selection for candidate registration.
```
[Waiter] [Hostess]
[Barman] [Registrar]
```

#### `get_onboarding_gender_reply_keyboard()`

```
[Мужской] [Женский]
```

#### `get_onboarding_time_reply_keyboard(times)`

Dynamic time selection.
```
[08:00] [09:00] [10:00]
```

#### `get_onboarding_confirm_reply_keyboard()`

```
[✅ Подтвердить] [✏️ Изменить]
```

#### `get_candidate_card_keyboard()`

Candidate review actions.
```
[✅ Принять] [❌ Отклонить]
[➡️ Следующий]
[⬅️ Назад к управлению]
```

#### `get_set_times_keyboard(selected, event_id)`

Time assignment options.
```
[Назначить всем одинаковое время]
[👤 John Doe] [👤 Jane Smith] ...
[⬅️ Назад]
```

---

### Inline Keyboards

Buttons embedded in specific messages.

#### `get_event_post_creation_keyboard()`

Post-creation actions.
```
[📢 Опубликовать опрос] [👥 Перейти к отбору]
[📊 Логи]               [⚙️ Настройки]
```

#### `get_invitation_keyboard(event_id)`

Candidate invitation response.
```
[✅ Да, участвую] [❌ Нет, не могу]
```

#### `get_checkin_keyboard(event_id)`

Event day check-in.
```
[📍 Я пришел!]
```

#### `get_gender_inline_keyboard()`

Gender selection (inline).
```
[👨 Мужской] [👩 Женский]
```

#### `get_role_selection_keyboard()`

Initial role choice.
```
[👨‍💼 Я Рекрутер] [🙋‍♂️ Я Кандидат]
```

#### `get_onboarding_start_keyboard(event_id)`

Start registration.
```
[🚀 Начать регистрацию]
```

#### `get_confirm_keyboard()`

Generic confirm/cancel.
```
[✅ Подтвердить] [❌ Отмена]
```

---

## Validators

**File**: `utils/validators.py`

Input validation utilities.

### Functions

#### `validate_time_format(time_str: str) -> bool`

Validates `HH:MM` 24-hour format.

**Regex:** `^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$`

**Examples:**
```python
validate_time_format("09:00")   # True
validate_time_format("23:59")   # True
validate_time_format("25:00")   # False
validate_time_format("9:0")     # False
validate_time_format("abc")     # False
```

---

#### `validate_date_format(date_str: str) -> bool`

Validates `DD.MM.YYYY` format.

**Examples:**
```python
validate_date_format("15.04.2026")  # True
validate_date_format("1.1.2026")    # True
validate_date_format("2026-04-15")  # False (ISO format handled separately)
```

---

#### `validate_max_candidates(count: int) -> bool`

Validates candidate count is between 1 and 100.

```python
validate_max_candidates(10)   # True
validate_max_candidates(0)    # False
validate_max_candidates(150)  # False
```

---

## Exceptions

**File**: `utils/exceptions.py`

Custom exception hierarchy for error handling.

### Exception Hierarchy

```
NexusError (base)
├── DatabaseError
├── EventNotFoundError
├── AccessDeniedError
└── ValidationError
```

### Usage

```python
from utils.exceptions import EventNotFoundError, DatabaseError

async def get_event(event_id: str):
    result = db.query(...)
    if not result:
        raise EventNotFoundError(f"Event {event_id} not found")
    return result

# In handler
try:
    event = await get_event(event_id)
except EventNotFoundError:
    await message.reply_text("❌ Мероприятие не найдено.")
except DatabaseError as e:
    logger.error(f"DB error: {e}")
    await message.reply_text("⚠️ Ошибка базы данных.")
```

### Exception Classes

#### `NexusError`

Base exception for all custom errors.

```python
class NexusError(Exception):
    """Base exception for Nexus AI platform."""
    pass
```

---

#### `DatabaseError`

Wraps Supabase query errors.

```python
class DatabaseError(NexusError):
    """Database operation failed."""
    pass
```

---

#### `EventNotFoundError`

Raised when event lookup fails.

```python
class EventNotFoundError(NexusError):
    """Event not found in database."""
    pass
```

---

#### `AccessDeniedError`

Raised when user lacks permissions.

```python
class AccessDeniedError(NexusError):
    """User does not have permission for this action."""
    pass
```

---

#### `ValidationError`

Raised when input validation fails.

```python
class ValidationError(NexusError):
    """Input validation failed."""
    pass
```

---

## Keyboard Usage Patterns

### Reply Keyboard vs Inline Keyboard

| Feature | Reply Keyboard | Inline Keyboard |
|---------|---------------|-----------------|
| **Persistence** | Stays visible until replaced | One-time, disappears after click |
| **Use Case** | Navigation menus, dashboards | Context-specific actions |
| **Callback Data** | No (triggers MessageHandler) | Yes (triggers CallbackQueryHandler) |
| **Examples** | Recruiter dashboard, event list | Candidate accept/reject, invitations |

### Building a Custom Keyboard

```python
from telegram import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup

# Reply keyboard
reply_kb = ReplyKeyboardMarkup(
    [
        [KeyboardButton("Button 1"), KeyboardButton("Button 2")],
        [KeyboardButton("Button 3")]
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)
await message.reply_text("Choose:", reply_markup=reply_kb)

# Inline keyboard
inline_kb = InlineKeyboardMarkup([
    [InlineKeyboardButton("Accept", callback_data=f"accept:{event_id}:{user_id}")],
    [InlineKeyboardButton("Reject", callback_data=f"reject:{event_id}:{user_id}")]
])
await message.reply_text("Decision:", reply_markup=inline_kb)
```

---

[← Handlers](handlers.md) | [← Back to README](../README.md)
