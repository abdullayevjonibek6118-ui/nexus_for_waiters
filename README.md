# Nexus AI — B2B SaaS Event Staffing Platform

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Nexus AI is a full-featured B2B SaaS Telegram bot platform for intelligent event staffing and recruitment. It supports multi-tenancy, enabling platform owners to sell subscription-based access to recruitment agencies and event companies.

---

## 📑 Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Quick Start](#quick-start)
- [Environment Variables](#environment-variables)
- [Bot Commands](#bot-commands)
- [Database Schema](#database-schema)
- [Application Status Flow](#application-status-flow)
- [Project Structure](#project-structure)
- [Documentation](#documentation)
- [Common Issues & Troubleshooting](#common-issues--troubleshooting)
- [Contributing](#contributing)
- [License](#license)

---

## 🌟 Overview

Nexus AI streamlines the event staffing workflow by connecting three key roles:

1. **Platform Owner (Super Admin)** — Manages companies, subscriptions, and platform-wide operations
2. **Recruiters** — Create events, publish hiring announcements, review candidates, assign shifts, and generate reports
3. **Candidates** — Register for events, respond to invitations, and check-in on event day

The platform ensures complete data isolation between companies, with subscription-based access control and audit logging.

---

## ✨ Key Features

### 👑 For Platform Owners (Super Admin)
- **Company Management**: Create companies, set monthly subscription fees
- **Recruiter Management**: Assign recruiters to specific companies
- **Subscription Control**: Extend subscriptions (1-12 months), automatic blocking on expiry
- **Data Isolation**: Each company operates in isolated multi-tenant space
- **Custom Groups**: Assign dedicated Telegram group chat IDs for each company's hiring announcements

### 👨‍💼 For Recruiters
- **Event Creation**: 9-step guided conversation (title, date, location, payment, headcount, gender split, roles, arrival times, end time)
- **Hiring Announcements**: Publish to company's Telegram group with deep-link registration button
- **Candidate Review**: Card-by-card applicant review with accept/reject functionality
- **Time Assignment**: Bulk or individual arrival/departure time scheduling
- **Google Sheets Integration**: Auto-generate spreadsheets with candidate data and payment calculations
- **Excel Export**: Generate `.xlsx` reports with auto-calculated formulas
- **Candidate Notifications**: Mass broadcast invitations with confirmation tracking
- **Auto-Select**: Bulk-accept N candidates from applicant pool
- **Audit Logs**: Complete action history per event
- **Event Archiving**: Close events with automatic Telegram post updates

### 🙋‍♂️ For Candidates
- **Simple Registration**: Role, phone, name, gender, time preference (5-step onboarding)
- **Event-Specific Roles**: Apply for specific positions on specific events
- **Invitation Management**: Accept/decline invitations via inline buttons
- **Check-In System**: One-tap "I arrived" notification on event day
- **Profile Persistence**: Cross-event profile retention (no repeated registration)

---

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Telegram Bot API                        │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                     main.py (Entry Point)                    │
│  • Handler Registration                                     │
│  • PicklePersistence (state across restarts)                │
│  • APScheduler Initialization                               │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                      handlers/                               │
│  • start.py          • admin_handler.py                     │
│  • event_handler.py  • candidate_handler.py                 │
│  • poll_handler.py   • onboarding_handler.py                │
│  • super_admin_handler.py • role_handler.py                 │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                      services/                               │
│  • event_service.py       • candidate_service.py            │
│  • company_service.py     • recruiter_service.py            │
│  • sheets_service.py      • excel_service.py                │
│  • scheduler_service.py   • audit_service.py                │
└────────────────────────┬────────────────────────────────────┘
                         │
          ┌──────────────┴──────────────┐
          ▼                             ▼
┌──────────────────┐          ┌──────────────────┐
│   Supabase DB    │          │  Google Sheets   │
│  • companies     │          │  (Auto-generated │
│  • recruiters    │          │   spreadsheets)  │
│  • events        │          └──────────────────┘
│  • candidates    │
│  • event_cands   │          ┌──────────────────┐
│  • event_logs    │          │   APScheduler    │
└──────────────────┘          │  • Payment       │
                              │    Reminders     │
                              │  • Daily         │
                              │    Notifications │
                              └──────────────────┘
```

**Key Architectural Patterns:**
- **Layered Architecture**: Handlers → Services → Models → Database
- **ConversationHandler**: Multi-step flows (event creation, onboarding)
- **State Machine**: Application lifecycle with enforced transitions
- **Multi-Tenancy**: Company-scoped data isolation
- **Deep Linking**: `/start event_<id>` for event-specific registration

---

## 🛠 Tech Stack

| Component | Technology |
|-----------|-----------|
| **Language** | Python 3.10+ |
| **Telegram Bot** | python-telegram-bot >= 21.0 |
| **Database** | Supabase (PostgreSQL) 2.7.4 |
| **Data Validation** | Pydantic >= 2.10, pydantic-settings >= 2.7 |
| **Scheduler** | APScheduler >= 3.10.4 |
| **Google Integration** | google-api-python-client >= 2.114 |
| **Excel Export** | openpyxl >= 3.1.2 |
| **Timezone** | pytz >= 2024.1 |
| **Environment** | python-dotenv >= 1.0.0 |

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10 or higher
- Supabase account (free tier available)
- Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- Google Service Account credentials (optional, for Sheets integration)

### 1. Clone & Install Dependencies

```bash
git clone <repository-url>
cd nexus_for_waiters
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file in the project root:

```env
# Telegram Bot
BOT_TOKEN=your_bot_token_here
SUPER_ADMIN_ID=123456789
ADMIN_USER_IDS=
GROUP_CHAT_ID=

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_service_role_key_here

# Google Sheets (Optional)
GOOGLE_CREDENTIALS_FILE=credentials/google_service_account.json
GOOGLE_SERVICE_ACCOUNT_EMAIL=your-sa@project.iam.gserviceaccount.com

# Scheduler
TIMEZONE=Asia/Tashkent

# Logging
LOG_LEVEL=INFO
```

### 3. Set Up Database

1. Open your Supabase project → SQL Editor
2. Execute the entire `supabase_schema.sql` script
3. This creates 6 tables: `companies`, `recruiters`, `events`, `candidates`, `event_candidates`, `event_logs`

### 4. Google Sheets Setup (Optional)

1. Create a Google Service Account
2. Download the JSON credentials
3. Place at `credentials/google_service_account.json`
4. Share the service account email with your spreadsheet

### 5. Run the Bot

```bash
python main.py
```

You should see:
```
🚀 Запуск Nexus AI Bot...
✅ Планировщик задач запущен
✅ Все хендлеры зарегистрированы. Запуск polling...
```

---

## 🔐 Environment Variables

| Variable | Type | Required | Description |
|----------|------|----------|-------------|
| `BOT_TOKEN` | string | ✅ | Telegram Bot Token from [@BotFather](https://t.me/BotFather) |
| `SUPER_ADMIN_ID` | int | ✅ | Your Telegram User ID (get from [@userinfobot](https://t.me/userinfobot)) |
| `ADMIN_USER_IDS` | string | ❌ | Comma-separated admin IDs (deprecated, use `SUPER_ADMIN_ID`) |
| `GROUP_CHAT_ID` | int | ❌ | Fallback group chat ID for polls (use company settings instead) |
| `SUPABASE_URL` | string | ✅ | Your Supabase project URL |
| `SUPABASE_KEY` | string | ✅ | Supabase **service_role** key (bypasses RLS) |
| `GOOGLE_CREDENTIALS_FILE` | string | ❌ | Path to Google SA JSON file |
| `GOOGLE_SERVICE_ACCOUNT_EMAIL` | string | ❌ | Google SA email |
| `TIMEZONE` | string | ❌ | Timezone for scheduler (default: `Asia/Tashkent`) |
| `LOG_LEVEL` | string | ❌ | Logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR` |

---

## 📜 Bot Commands

### Super Admin Commands
| Command | Description |
|---------|-------------|
| `/owner` | Open SaaS management panel (create companies, add recruiters, extend subscriptions) |
| `/list_events` | View all platform events |
| `/logs <event_id>` | View audit logs for an event |

### Recruiter Commands
| Command | Description |
|---------|-------------|
| `/start` | Open role-based dashboard |
| `/events` | Main recruiter dashboard (Reply keyboard menu) |
| `/create_event` | Start 9-step event creation wizard |
| `/list_events` | List active events |
| `/voters <event_id>` | List all applicants |
| `/candidates <event_id>` | Review candidates card-by-card |
| `/set_times <event_id>` | Assign arrival/departure times |
| `/notify_candidates <event_id>` | Send invitations to accepted candidates |
| `/export_excel <event_id>` | Generate and download XLSX report |
| `/create_sheet <event_id>` | Create Google Sheet for selected candidates |
| `/payment_reminder <event_id>` | Schedule 14-day payment reminder |
| `/payment_confirmed <event_id>` | Confirm payment and cancel reminder |
| `/close_event <event_id>` | Archive event (updates Telegram post) |
| `/announce <event_id> <text>` | Mass broadcast to selected candidates |
| `/help` | Context-sensitive help |

### Candidate Commands
| Command | Description |
|---------|-------------|
| `/start event_<id>` | Register for specific event |
| `/help` | Candidate help and profile info |

---

## 🗄 Database Schema

### Tables

#### `companies`
SaaS tenants with subscription management.
- `id` (UUID, PK)
- `name` (TEXT)
- `subscription_until` (TIMESTAMPTZ)
- `monthly_fee` (NUMERIC)
- `group_chat_id` (BIGINT) — Telegram group for hiring announcements
- `status` (TEXT: `active`, `expired`, `disabled`)

#### `recruiters`
Maps Telegram users to companies.
- `user_id` (BIGINT, PK) — Telegram User ID
- `company_id` (UUID, FK → companies)
- `first_name`, `last_name` (TEXT)
- `is_active` (BOOLEAN)

#### `events`
Event details with channel post tracking.
- `event_id` (UUID, PK)
- `company_id` (UUID, FK → companies)
- `title`, `date`, `location`, `payment` (TEXT)
- `max_candidates`, `required_men`, `required_women` (INTEGER)
- `status` (TEXT: `DRAFT`, `ACTIVE`, `POLL_PUBLISHED`, `RECRUITING`, etc.)
- `poll_id`, `sheet_url` (TEXT)
- `required_roles`, `arrival_times` (JSONB)
- `end_time` (TEXT)
- **`channel_chat_id`**, **`channel_message_id`** (TEXT) — Telegram post references
- `created_by` (BIGINT) — Recruiter User ID

#### `candidates`
Global candidate profiles.
- `user_id` (BIGINT, PK)
- `first_name`, `last_name`, `full_name` (TEXT)
- `primary_role`, `phone_number`, `telegram_username` (TEXT)
- `gender` (TEXT: `Male`, `Female`)
- `has_messaged_bot` (BOOLEAN)

#### `event_candidates`
Join table with application tracking.
- `id` (UUID, PK)
- `event_id`, `user_id` (UUID/BIGINT, FKs)
- `application_status` (TEXT: `PENDING`, `ACCEPTED`, `INVITED`, `CONFIRMED`, `CHECKED_IN`, `REJECTED`, `DECLINED`)
- `role`, `arrival_time`, `departure_time` (TEXT)
- Legacy fields: `vote_status`, `selected`, `confirmed`, `is_checked_in`, `is_checkin_confirmed`

#### `event_logs`
Audit trail for all actions.
- `log_id` (UUID, PK)
- `event_id` (UUID, FK)
- `action` (TEXT)
- `performed_by` (BIGINT)
- `timestamp` (TIMESTAMPTZ)
- `details` (JSONB)

---

## 🔄 Application Status Flow

### Candidate Application Lifecycle
```
PENDING
   ├──→ ACCEPTED ──→ SCHEDULED ──→ INVITED ──→ CONFIRMED ──→ CHECKED_IN
   │       │                          │            │
   │       ├──→ REJECTED              ├──→ DECLINED ├──→ DECLINED
   │       └──→ INVITED               └──→ REJECTED
   └──→ REJECTED
```

**Valid Transitions:**
- `PENDING` → `ACCEPTED`, `REJECTED`
- `ACCEPTED` → `SCHEDULED`, `INVITED`, `REJECTED`
- `SCHEDULED` → `INVITED`, `REJECTED`
- `INVITED` → `CONFIRMED`, `DECLINED`
- `CONFIRMED` → `CHECKED_IN`, `DECLINED`
- `CHECKED_IN`, `REJECTED`, `DECLINED` → Terminal (no further transitions)

### Event Lifecycle
```
DRAFT → ACTIVE → POLL_PUBLISHED → RECRUITING →
SELECTION_COMPLETED → TIMES_ASSIGNED → SHEET_GENERATED →
CANDIDATES_CONFIRMED → COMPLETED → PAYMENT_PENDING → CLOSED
```

---

## 📁 Project Structure

```
nexus_for_waiters/
├── main.py                        # Entry point: handler registration, bot startup
├── config.py                      # Pydantic Settings singleton
├── database.py                    # Supabase client singleton
├── requirements.txt               # Python dependencies
├── supabase_schema.sql            # Complete database schema
├── Instructions.md                # Super Admin setup guide
├── Instructions.txt               # Detailed architecture doc
│
├── handlers/
│   ├── __init__.py
│   ├── start.py                   # /start, /help, deep linking, role routing
│   ├── admin_handler.py           # /create_sheet, /export_excel, /close_event, /announce, /logs
│   ├── super_admin_handler.py     # /owner panel (ConversationHandler)
│   ├── event_handler.py           # /create_event (9-step CH), /events dashboard, event management
│   ├── candidate_handler.py       # /voters, /candidates, /set_times, /notify, check-in flow
│   ├── onboarding_handler.py      # Candidate registration (7-state CH)
│   ├── poll_handler.py            # /publish_poll, /close_poll
│   └── role_handler.py            # Role selection (Reply/Inline keyboards)
│
├── models/
│   ├── __init__.py
│   ├── event.py                   # Pydantic Event model
│   ├── candidate.py               # Pydantic Candidate model
│   └── event_candidate.py         # EventCandidate + state machine (ALLOWED_TRANSITIONS)
│
├── services/
│   ├── __init__.py
│   ├── event_service.py           # Event CRUD, save_poll_published_info
│   ├── candidate_service.py       # apply_for_event, transition_application, get_applicants
│   ├── company_service.py         # Company CRUD, subscription checks
│   ├── recruiter_service.py       # Recruiter management
│   ├── sheets_service.py          # Google Sheets creation
│   ├── excel_service.py           # XLSX generation with formulas
│   ├── scheduler_service.py       # APScheduler: payment reminders, daily notifications
│   └── audit_service.py           # Event logging (event_logs table)
│
├── utils/
│   ├── __init__.py
│   ├── constants.py               # Enums: EventStatus, ApplicationStatus, CandidateRole, etc.
│   ├── keyboards.py               # All Inline/Reply keyboard builders
│   ├── validators.py              # Time/date format validators
│   └── exceptions.py              # Custom exceptions (DatabaseError, EventNotFoundError, etc.)
│
└── docs/                          # Detailed module documentation
    ├── models.md
    ├── services.md
    ├── handlers.md
    └── utils.md
```

---

## 📚 Documentation

For detailed module documentation, see:

- [Models Documentation](docs/models.md) — Data models and state machine
- [Services Documentation](docs/services.md) — Business logic layer
- [Handlers Documentation](docs/handlers.md) — Telegram interaction layer
- [Utils Documentation](docs/utils.md) — Constants, keyboards, validators, exceptions
- [Architecture Guide](ARCHITECTURE.md) — System architecture and component interaction
- [Contributing Guide](CONTRIBUTING.md) — Development guidelines
- [Changelog](CHANGELOG.md) — Version history

---

## ⚠️ Common Issues & Troubleshooting

### 1. Bot doesn't respond to `/start event_<id>`
**Solution**: Ensure deep linking format is correct: `https://t.me/<bot_username>?start=event_<event_id>`

### 2. "⛔ У вас нет прав" error
**Solution**: Verify recruiter is added to a company via `/owner` panel and company subscription is active.

### 3. Google Sheet creation fails
**Solution**:
- Check `GOOGLE_CREDENTIALS_FILE` path in `.env`
- Ensure service account JSON is valid
- Verify service account has Sheets API enabled

### 4. Subscription expired error
**Solution**: Use `/owner` → Select company → "Продлить подписку" → Choose months

### 5. Event not found
**Solution**: Ensure event ID is correct. Use `/list_events` to see active events.

### 6. Telegram post not updating on `/close_event`
**Solution**: Check that `channel_chat_id` and `channel_message_id` exist in the events table. These are set automatically when `/publish_poll` is called.

### 7. Scheduler not sending reminders
**Solution**:
- Verify `TIMEZONE` is correct in `.env`
- Check bot has permission to message admin IDs
- Ensure company subscription is active

---

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines, local setup, and deployment instructions.

---

## 📄 License

This project is licensed under the MIT License.

---

*Developed for Nexus AI Platform*
