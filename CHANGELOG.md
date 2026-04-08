# Changelog

All notable changes to the Nexus AI platform.

**Format:** [Semantic Versioning](https://semver.org/) — `Major.Minor.Patch`

---

## [Unreleased]

### Added

- **Comprehensive documentation suite:**
  - Updated `README.md` with full project overview, architecture diagram, command tables, and troubleshooting guide
  - Created `docs/models.md` — Detailed data model documentation
  - Created `docs/services.md` — Business logic layer reference
  - Created `docs/handlers.md` — Telegram interaction layer guide
  - Created `docs/utils.md` — Constants, keyboards, validators, exceptions reference
  - Created `ARCHITECTURE.md` — System architecture and component interaction
  - Created `CONTRIBUTING.md` — Development guidelines and deployment instructions
  - Created `CHANGELOG.md` — This file

---

## [1.2.0] — 2026-04-08

### Added

- **Channel post tracking for event archiving:**
  - Added `channel_chat_id` column to `events` table and `Event` model
  - Added `channel_message_id` column to `events` table and `Event` model
  - These fields store Telegram chat and message IDs for published hiring announcements
  - Enables automatic post updates when events are archived

- **Unified poll publication info saving:**
  - Created `save_poll_published_info()` function in `services/event_service.py`
  - Single UPDATE query sets 4 fields: `poll_id`, `status`, `channel_chat_id`, `channel_message_id`
  - Replaces separate status update and poll ID save operations
  - Called from `/publish_poll` handler after successful message send

- **Enhanced event archiving with Telegram post updates:**
  - `/close_event` now attempts to edit the original channel post to add "🔴 ЗАКРЫТО" status
  - Removes inline keyboard buttons from archived posts
  - Handles text posts via `edit_message_text()`
  - Handles media posts via `edit_message_caption()` when text edit fails with "There is no text in the message to edit"
  - Provides detailed feedback to recruiter about post update success/failure
  - Gracefully handles missing `channel_chat_id`/`channel_message_id` (events published before this feature)

- **Improved date parsing in event creation:**
  - Added support for Russian date formats: "15 апреля", "15 апреля 2026"
  - Added support for European format: "15.04.2026"
  - Maintains ISO format support: "2026-04-15"
  - Auto-assumes current year when not specified
  - Implemented in `parse_russian_date()` function in `handlers/event_handler.py`

### Changed

- **Event creation wizard date validation:**
  - Replaced simple `validate_date_format()` with intelligent `parse_russian_date()` parser
  - Better user experience with multiple input format support
  - Clearer error messages with format examples

- **Event model structure:**
  - Added `channel_chat_id: Optional[str] = None` field
  - Added `channel_message_id: Optional[str] = None` field
  - Fields populated during event creation if provided

### Technical Details

**Database Migration Required:**
```sql
ALTER TABLE events ADD COLUMN channel_chat_id TEXT;
ALTER TABLE events ADD COLUMN channel_message_id TEXT;
```

**API Changes:**
- `event_service.save_poll_published_info()` now accepts `chat_id` and `message_id` parameters
- `event_service.create_event()` now accepts `channel_chat_id` and `channel_message_id` from Event model

---

## [1.1.0] — 2026-03-15

### Added

- **Multi-tenancy with company data isolation:**
  - Added `company_id` to `events` table
  - Added `companies` table with subscription management
  - Added `recruiters` table linking Telegram users to companies
  - All recruiter commands enforce company ownership checks
  - Super Admin bypasses all isolation checks

- **Subscription management system:**
  - `/owner` panel for company creation and management
  - Subscription expiration checks before allowing recruiter actions
  - Automatic blocking of expired subscriptions
  - Extend subscription by 1-12 months via conversation flow

- **Company-specific group chat IDs:**
  - Added `group_chat_id` to `companies` table
  - Each company can have dedicated Telegram group for hiring announcements
  - Fallback to global `GROUP_CHAT_ID` if company setting not configured
  - Set via `/owner` → Manage company → "Указать ID группы"

- **Application status state machine:**
  - Created `ApplicationStatus` enum with 8 states
  - Defined `ALLOWED_TRANSITIONS` dict enforcing valid state changes
  - Implemented `can_transition()` validation function
  - `transition_application()` service function enforces state machine
  - Prevents invalid status combinations

- **Candidate profile system:**
  - Global candidate profiles persist across events
  - Profile includes: full_name, phone_number, telegram_username, gender, primary_role
  - Event-specific applications track: role, arrival_time, departure_time, application_status
  - N+1 query fix: `get_applicants()` uses join query to fetch profiles in single request

- **Reply keyboard-driven UX:**
  - Replaced inline keyboards with Reply keyboards for recruiter navigation
  - Persistent bottom buttons: "🆕 Создать мероприятие", "📋 Мои мероприятия", "📊 Отчеты", "❓ Помощь"
  - Event action buttons: "📢 Опубликовать", "👥 Карточки", "✉️ Уведомить", etc.
  - Candidate card navigation: "✅ Принять", "❌ Отклонить", "➡️ Следующий"
  - Improved mobile UX with larger touch targets

### Changed

- **Event creation from inline to Reply keyboard:**
  - `/events` dashboard now shows Reply keyboard menu
  - Event selection via button click instead of inline callback
  - Session management via `context.user_data["ev_list"]`

- **Candidate review from inline to card-based Reply:**
  - `/candidates` shows cards one-by-one with Reply navigation
  - State stored in `context.user_data["cards_{event_id}"]`
  - Accept/reject actions trigger `transition_application()`

- **Time assignment simplified:**
  - `/set_times` shows list of accepted candidates with Reply buttons
  - "Назначить всем" for bulk time assignment
  - Individual candidate time setting via button click
  - Time input via simple text: "09:00 20:00"

### Fixed

- **Foreign key guard in onboarding:**
  - Bug-05 fix: Create candidate profile before event registration
  - Prevents FK constraint violations in `event_candidates` table
  - `get_or_create_candidate()` called before `apply_for_event()`

- **Onboarding edit flow data cleanup:**
  - UI-02 fix: Clear all `ob_*` keys from `user_data` when candidate chooses "Изменить"
  - Added `ob_gender` to cleanup list (was previously missed)
  - Prevents stale data from being used in registration

- **Duplicate gender update function:**
  - Bug-6 fix: Removed duplicate `update_gender()` function
  - Canonical version is `update_candidate_gender()`

---

## [1.0.0] — 2026-02-01

### Initial Release

#### Core Features

- **Telegram bot with python-telegram-bot 21+**
- **Supabase database integration** with 6 tables: `companies`, `recruiters`, `events`, `candidates`, `event_candidates`, `event_logs`
- **Event creation wizard** (9-step ConversationHandler)
- **Candidate onboarding** (7-state ConversationHandler with deep linking)
- **Poll publishing** to Telegram groups with registration buttons
- **Candidate review** via card interface
- **Time assignment** for accepted candidates
- **Google Sheets integration** for candidate reporting
- **Excel export** with auto-calculated payment formulas
- **Mass candidate notifications** with delivery tracking
- **Audit logging** for all event actions
- **Payment reminder scheduler** (14-day delayed notifications)
- **Daily event reminders** to confirmed candidates (cron at 18:00)
- **Super Admin panel** for SaaS management

#### Architecture

- **Layered design:** Handlers → Services → Models → Database
- **Multi-role support:** Super Admin, Recruiter, Candidate
- **Deep linking:** `/start event_<id>` for event-specific registration
- **Conversation persistence:** PicklePersistence for state across restarts
- **Async/await:** Full async support with thread offloading for blocking calls

#### Database Schema

- Row Level Security (RLS) enabled
- Service role key bypasses RLS for bot access
- Foreign key constraints with CASCADE deletes
- Performance indexes on frequently queried columns

#### External Integrations

- **Google Sheets API:** Auto-generate spreadsheets with formatting
- **openpyxl:** Generate `.xlsx` reports with formulas
- **APScheduler:** Background task scheduling
- **Telegram Bot API:** Long polling communication

---

## Version History Summary

| Version | Release Date | Key Changes |
|---------|-------------|-------------|
| **1.0.0** | 2026-02-01 | Initial release with core features |
| **1.1.0** | 2026-03-15 | Multi-tenancy, state machine, Reply keyboard UX |
| **1.2.0** | 2026-04-08 | Channel post tracking, enhanced archiving |
| **Unreleased** | — | Comprehensive documentation |

---

## Database Migration History

### Migration 1.1.0 (Multi-tenancy)

```sql
-- New tables
CREATE TABLE companies (...);
CREATE TABLE recruiters (...);

-- Modified tables
ALTER TABLE events ADD COLUMN company_id UUID REFERENCES companies(id);
ALTER TABLE events ADD COLUMN required_men INTEGER DEFAULT 0;
ALTER TABLE events ADD COLUMN required_women INTEGER DEFAULT 0;

-- New indexes
CREATE INDEX idx_events_company_id ON events(company_id);
```

### Migration 1.2.0 (Channel Post Tracking)

```sql
ALTER TABLE events ADD COLUMN channel_chat_id TEXT;
ALTER TABLE events ADD COLUMN channel_message_id TEXT;
```

---

## Upgrade Instructions

### Upgrading to 1.2.0

1. **Backup database:**
   ```bash
   pg_dump -h db.your-supabase.com -U postgres nexus > backup_1.1.0.sql
   ```

2. **Run migration:**
   ```sql
   ALTER TABLE events ADD COLUMN channel_chat_id TEXT;
   ALTER TABLE events ADD COLUMN channel_message_id TEXT;
   ```

3. **Deploy new code:**
   ```bash
   git pull
   pip install -r requirements.txt  # if dependencies changed
   python main.py
   ```

4. **Verify:**
   - Create test event
   - Publish poll
   - Check `channel_chat_id` and `channel_message_id` are saved
   - Close event and verify Telegram post updates

### Upgrading to 1.1.0

1. **Run schema migration** (`supabase_schema.sql` includes all tables)

2. **Update `.env`:**
   - Ensure `SUPER_ADMIN_ID` is set (required for new multi-tenancy)

3. **Create your company:**
   ```
   /owner → Создать компанию → [name] → [monthly_fee]
   ```

4. **Add recruiters to company:**
   ```
   /owner → Список компаний → [company] → Добавить рекрутера → [user_id]
   ```

5. **Set group chat ID:**
   ```
   /owner → Список компаний → [company] → Указать ID группы → [chat_id]
   ```

---

[← Back to README](README.md)
