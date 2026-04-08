# Handlers Documentation

Telegram interaction layer for the Nexus AI platform. Handlers route user actions to services.

---

## Table of Contents

- [Start Handler](#start-handler)
- [Admin Handler](#admin-handler)
- [Super Admin Handler](#super-admin-handler)
- [Event Handler](#event-handler)
- [Candidate Handler](#candidate-handler)
- [Onboarding Handler](#onboarding-handler)
- [Poll Handler](#poll-handler)
- [Role Handler](#role-handler)

---

## Start Handler

**File**: `handlers/start.py`

Handles `/start` and `/help` commands with role-based routing.

### `/start` Command Flow

```
/start
   │
   ├─ Has deep link? (event_<id>)
   │   └─→ Start onboarding for event
   │
   ├─ Is Super Admin?
   │   └─→ Show admin dashboard with inline keyboard
   │
   ├─ Is Recruiter?
   │   ├─ Subscription active?
   │   │   └─→ Show recruiter welcome
   │   └─ Subscription expired?
   │       └─→ Show expiration warning
   │
   ├─ Is Candidate?
   │   ├─ Has gender?
   │   │   └─→ Show candidate dashboard + contact button
   │   └─ No gender?
   │       └─→ Prompt gender selection
   │
   └─ New user?
       └─→ Show role selection keyboard
```

### Deep Linking

Format: `https://t.me/<bot_username>?start=event_<event_id>`

When a candidate clicks a registration button on a hiring announcement, the bot receives `/start event_<id>` and routes to `onboarding_handler.start_onboarding()`.

### `/help` Command

Returns context-sensitive help based on user role:
- **Super Admin**: Lists `/owner`, `/list_events`, `/logs`
- **Recruiter**: Lists all recruiter commands with descriptions
- **Candidate**: Explains registration and check-in process

---

## Admin Handler

**File**: `handlers/admin_handler.py`

Commands for recruiters and super admins.

### Commands

#### `/create_sheet <event_id>`

Creates a Google Spreadsheet with selected candidates.

**Flow:**
1. Validate recruiter permissions
2. Get event and verify company ownership
3. Get selected candidates (`application_status=ACCEPTED`)
4. Call `sheets_service.create_event_sheet()`
5. Save URL to event via `event_service.save_sheet_url()`
6. Log action and send link to recruiter

---

#### `/payment_reminder <event_id>`

Schedules a payment reminder for 14 days in the future.

**Flow:**
1. Validate permissions
2. Call `scheduler_service.schedule_payment_reminder()`
3. Update event status to `PAYMENT_PENDING`
4. Log action

---

#### `/payment_confirmed <event_id>`

Cancels payment reminder and marks event as completed.

**Flow:**
1. Cancel scheduled job
2. Update event status to `SELECTION_COMPLETED`
3. Log action

---

#### `/logs <event_id>`

Shows last 15 audit log entries for an event.

**Output format:**
```
🕐 2026-04-08 14:30:00
   🔸 event_closed (by 123456789)
```

---

#### `/close_event <event_id>`

Archives an event and updates the Telegram announcement post.

**Flow:**
1. Validate permissions
2. Update event status to `CLOSED`
3. **Attempt to update Telegram post:**
   - Check if `channel_chat_id` and `channel_message_id` exist
   - Try `edit_message_text()` to add "🔴 ЗАКРЫТО" and remove buttons
   - If fails with "There is no text in the message to edit", try `edit_message_caption()` (for media posts)
   - Log success/error
4. Send confirmation to recruiter with post update status

**Key Implementation Details:**
- Uses `reply_markup=None` to remove inline buttons
- Handles both text and media posts gracefully
- Provides detailed error feedback if post update fails

---

#### `/export_excel <event_id>`

Generates and sends an `.xlsx` file with candidate data.

**Flow:**
1. Validate permissions
2. Get selected candidates (fallback to all applicants if none selected)
3. Call `excel_service.generate_event_xlsx()` in thread
4. Send file document with 60s timeout
5. Delete temporary file in `finally` block

---

#### `/announce <event_id> <message>`

Mass broadcasts a message to all selected candidates.

**Flow:**
1. Parse event_id and message text
2. Get selected candidates
3. Send message to each candidate individually
4. Track sent/failed counts
5. Log action and report results

---

## Super Admin Handler

**File**: `handlers/super_admin_handler.py`

SaaS owner panel for managing companies and subscriptions.

### `/owner` Command

Shows main menu with two options:
- **Создать компанию** (Create company)
- **Список компаний** (List companies)

### Conversation Flows

#### Create Company
```
sa:create_company
   → Input: Company name
   → Input: Monthly fee (number)
   → Create company in DB
   → Show confirmation with company ID
```

#### Add Recruiter
```
sa:add_rec:<company_id>
   → Input: Telegram user ID (number)
   → Add recruiter to company
   → Show confirmation
```

#### Extend Subscription
```
sa:sub:<company_id>
   → Input: Number of months (1-12)
   → Calculate: now() + 30 * months
   → Update subscription_until
   → Show new expiration date
```

#### Set Group Chat ID
```
sa:set_group:<company_id>
   → Input: Telegram chat ID (negative number for supergroups)
   → Update companies.group_chat_id
   → Show confirmation
```

### Callback Handler: `sa_callback_handler`

Handles inline button clicks:
- `sa:list_companies`: Lists all companies with manage buttons
- `sa:manage:<company_id>`: Shows company details with action buttons
- `sa:main`: Returns to main menu

---

## Event Handler

**File**: `handlers/event_handler.py`

Event creation and management.

### `/create_event` Conversation (9 Steps)

```
E_TITLE      → Input: Event name
E_DATE       → Input: Date (supports Russian format: "15 апреля", "15.04.2026")
E_LOC        → Input: Location/address
E_PAYMENT    → Input: Payment (auto-adds ₽ if missing)
E_MAX        → Input: Number of candidates (integer)
E_GENDERS    → Input: Gender split (e.g., "М-5 Ж-5" or "0")
E_ROLES      → Input: Comma-separated roles (e.g., "Waiter, Hostess")
E_TIMES      → Input: Comma-separated arrival times (e.g., "08:00, 09:00")
E_END_TIME   → Input: End time (e.g., "22:00")
   → Create event in DB
   → Show confirmation with event details
```

### Date Parser

Supports multiple formats:
- ISO: `2026-04-15`
- European: `15.04.2026`
- Russian: `15 апреля`, `15 апреля 2026`

Auto-assumes current year if not specified.

### `/events` Dashboard

Shows recruiter dashboard with Reply keyboard:
- **🆕 Создать мероприятие** → Starts `/create_event`
- **📋 Мои мероприятия** → Shows event list
- **📊 Отчеты** → Shows stats + company report download
- **❓ Помощь** → Shows help

### `/list_events`

Shows active events as Reply buttons. Stores event list in `context.user_data["ev_list"]` for later lookup.

### Event Selection & Management

When recruiter clicks an event from the list:
1. `handle_event_selection()` matches event name to ID
2. `show_event_management_menu()` displays event details with action buttons:
   - **📢 Опубликовать** → Publish hiring poll
   - **👥 Карточки** → Review candidates
   - **✉️ Уведомить** → Send invitations
   - **📄 Экспорт Excel** → Download XLSX
   - **⏰ Назначить время** → Set arrival times
   - **🤖 Автоотбор** → Auto-select N candidates
   - **📊 Логи** → View audit logs
   - **❌ Архивировать** → Close event

### `handle_event_action_callback`

Handles inline callback buttons for event management (legacy support). Routes to appropriate handler functions by action name.

---

## Candidate Handler

**File**: `handlers/candidate_handler.py`

Candidate review and management commands.

### `/voters <event_id>`

Lists all applicants with vote status emoji.

**Output:**
```
👥 Проголосовавшие (5):

✅ John Doe (@johndoe)
🤔 Jane Smith (@janesmith)
❌ Bob Johnson
```

---

### `/candidates <event_id>`

Shows candidate cards one-by-one with navigation.

**Flow:**
1. Get all applicants with profiles (single join query)
2. Store in `context.user_data["cards_{event_id}"]` with index
3. Render first card with accept/reject/next buttons

**Card Display:**
```
🙋‍♂️ Карточка кандидата
📦 1 из 5
━━━━━━━━━━━━━━━━━━━━━

👤 ФИО: John Doe
🔗 Профиль: @johndoe
👨 Пол: Мужской
🎭 Роль: Waiter
⏰ Время: 08:00
📱 Телефон: +79001234567
```

**Navigation:**
- **✅ Принять** → `transition_application(ACCEPTED)` → Next card
- **❌ Отклонить** → `transition_application(REJECTED)` → Next card
- **➡️ Следующий** → Next card (no status change)
- **⬅️ Назад к управлению** → Return to event menu

---

### `/set_times <event_id>`

Assigns arrival/departure times to accepted candidates.

**Modes:**
1. **Individual**: Click candidate button → Enter times
2. **Bulk**: Click "Назначить всем" → Enter times once for all

**Input format:** `HH:MM HH:MM` (e.g., `09:00 20:00`)

---

### `/notify_candidates <event_id>`

Sends invitations to accepted candidates with inline buttons.

**Flow:**
1. Get candidates with `ACCEPTED` status
2. For each candidate:
   - Build personalized message with event details and assigned times
   - Send message with invitation keyboard (Yes/No buttons)
   - `transition_application(INVITED)`
3. Update event status to `CANDIDATES_CONFIRMED`
4. Report sent/failed counts

### Candidate Confirmation Callback

When candidate clicks **Yes** on invitation:
- `transition_application(CONFIRMED)`
- Edit message to show confirmation
- Send check-in button for event day

When candidate clicks **No**:
- `transition_application(DECLINED)`
- Edit message to show decline confirmation

---

### Auto-Select (`auto_select_cmd`)

Bulk-accepts N candidates from applicant pool.

**Flow:**
1. Prompt for number
2. Accept first N candidates (in order of application)
3. Show confirmation

---

### Check-In Flow

#### `handle_checkin`

When candidate clicks "Я пришел" (I arrived):
1. `transition_application(CHECKED_IN)`
2. Notify recruiter with candidate name and confirm button

#### `handle_confirm_checkin_callback`

When recruiter clicks "Подтвердить приход":
1. `confirm_checkin(event_id, candidate_id)`
2. Edit message to show confirmation
3. Send confirmation message to candidate

---

### Gender & Contact Handlers

#### `handle_set_gender`

Saves candidate's gender and prompts for contact sharing.

#### `handle_contact`

Extracts phone number from Telegram contact object and prompts for full name.

#### `handle_general_name_input`

Saves full name and completes registration.

---

## Onboarding Handler

**File**: `handlers/onboarding_handler.py`

7-state ConversationHandler for candidate event registration.

### Flow

```
WAIT_REG_START  → Click "Start Registration" button
CHOOSE_ROLE     → Select role from event's required roles (Reply keyboard)
SHARE_PHONE     → Share contact (Telegram contact button)
INPUT_NAME      → Enter full name (text input)
CHOOSE_GENDER   → Select gender (Reply keyboard: Мужской/Женский)
CHOOSE_TIME     → Select arrival time from event's times (Reply keyboard)
CONFIRM_DATA    → Review all data → Confirm or Edit
```

### Confirmation Screen

Shows summary:
```
🏁 Почти готово! Проверьте данные:
━━━━━━━━━━━━━━━━━━

👤 ФИО: John Doe
🎭 Роль: Waiter
📱 Тел: +79001234567
⏰ Время: 08:00 — 22:00

Если всё верно, нажмите «Подтвердить».
```

### Edit Flow

"✏️ Изменить" button clears all `ob_*` keys from `user_data` and restarts from role selection.

### Registration Completion

On confirm:
1. Create/update candidate profile
2. Save full name, phone, gender
3. Call `apply_for_event()` with role and time
4. Log action
5. Show success message

---

## Poll Handler

**File**: `handlers/poll_handler.py`

Hiring announcement publication.

### `/publish_poll <event_id>`

Publishes hiring announcement to company's Telegram group.

**Flow:**
1. Validate recruiter permissions
2. Get event details
3. Get company's `group_chat_id` (fallback to global config)
4. Build announcement message with event details
5. Create inline keyboard with deep-link registration button
6. Send message to group chat
7. **Call `save_poll_published_info()`** to save:
   - `poll_id`
   - `status` → `POLL_PUBLISHED`
   - `channel_chat_id`
   - `channel_message_id`
8. Log action
9. Confirm to recruiter

### Message Format

```
📢 Работа на мероприятии

Corporate Party

📅 Дата: 2026-04-15
⏰ Начало: 08:00, 09:00
🏁 Конец: 22:00
📍 Место: Moscow, Red Street 1
💰 Оплата: 4000 ₽

Нужны сотрудники:
• Waiter
• Hostess

👇 Чтобы участвовать нажмите кнопку
```

Button: **[Зарегистрироваться]** → `https://t.me/<bot>?start=event_<id>`

### `/close_poll <event_id>`

Closes the hiring poll and marks event as `SELECTION_COMPLETED`.

---

## Role Handler

**File**: `handlers/role_handler.py`

Handles initial role selection for new users.

### Flow

1. User clicks "Я Рекрутер" or "Я Кандидат" (Reply keyboard)
2. **If Recruiter:**
   - Check if user is in recruiters table
   - If yes: Show recruiter dashboard
   - If no: Show "Contact admin" message
3. **If Candidate:**
   - Create candidate profile
   - Prompt gender selection

---

## Handler Registration

All handlers are registered in `main.py`:

```python
# Command handlers
app.add_handler(CommandHandler("start", start_command))
app.add_handler(CommandHandler("create_event", create_event_start_cmd))
app.add_handler(CommandHandler("publish_poll", publish_poll))
# ... more commands

# ConversationHandlers
app.add_handler(get_create_event_handler())
app.add_handler(get_onboarding_handler())
app.add_handler(get_super_admin_handler())

# Callback handlers
app.add_handler(CallbackQueryHandler(handle_event_action_callback, pattern=r"^(poll_publish|select|...)"))
app.add_handler(CallbackQueryHandler(handle_card_callback, pattern=r"^card_(accept|reject|next)"))
# ... more callbacks

# Message handlers (Reply keyboards)
app.add_handler(MessageHandler(filters.Regex(r"^(👨‍💼 Я Рекрутер|🙋‍♂️ Я Кандидат)"), handle_role_selection))
app.add_handler(MessageHandler(filters.Regex(r"^(🆕 Создать мероприятие|📋 Мои мероприятия|...)"), handle_recruiter_menu))
# ... more message handlers
```

---

[← Services](services.md) | [Utils →](utils.md)
