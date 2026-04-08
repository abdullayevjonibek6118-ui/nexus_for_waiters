# Contributing Guide

Development guidelines for the Nexus AI platform.

---

## Table of Contents

- [Local Development Setup](#local-development-setup)
- [Project Structure](#project-structure)
- [Code Style](#code-style)
- [Adding New Features](#adding-new-features)
- [Database Migrations](#database-migrations)
- [Testing](#testing)
- [Debugging](#debugging)
- [Deployment](#deployment)
- [Git Workflow](#git-workflow)

---

## Local Development Setup

### Prerequisites

- Python 3.10+
- Supabase account (free tier works)
- Telegram Bot Token
- Git

### 1. Clone Repository

```bash
git clone <repository-url>
cd nexus_for_waiters
```

### 2. Create Virtual Environment

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# Linux/Mac
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

Create `.env` file (see [README.md](README.md#environment-variables) for template):

```env
BOT_TOKEN=your_test_bot_token
SUPER_ADMIN_ID=your_telegram_id
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_service_role_key
TIMEZONE=Asia/Tashkent
LOG_LEVEL=DEBUG
```

### 5. Set Up Database

Run `supabase_schema.sql` in Supabase SQL Editor.

### 6. Run Bot

```bash
python main.py
```

---

## Project Structure

```
nexus_for_waiters/
├── main.py                 # Entry point
├── config.py               # Settings singleton
├── database.py             # Supabase client
├── handlers/               # Telegram interaction layer
├── services/               # Business logic layer
├── models/                 # Pydantic data models
├── utils/                  # Constants, keyboards, validators
├── docs/                   # Documentation
└── tests/                  # (Future) Unit tests
```

**Architecture:** Handlers → Services → Models → Database

---

## Code Style

### General Guidelines

1. **Language**: Code comments and docstrings in Russian (user-facing text in handlers can be Russian/English)
2. **Naming**:
   - Functions: `snake_case`
   - Classes: `PascalCase`
   - Constants: `UPPER_SNAKE_CASE`
   - Files: `snake_case.py`
3. **Imports**: Group imports (stdlib, third-party, local) with blank lines
4. **Error Handling**: Use custom exceptions from `utils/exceptions.py`
5. **Async**: All database/external API calls must be `async` or wrapped in `asyncio.to_thread()`

### Example Handler

```python
async def my_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Brief description of what this handler does."""
    # 1. Validate permissions
    if not await is_recruiter(update.effective_user.id):
        await update.effective_message.reply_text("⛔ У вас нет прав.")
        return

    # 2. Get data
    event_id = context.args[0] if context.args else None
    if not event_id:
        await update.effective_message.reply_text("Использование: /my_command <event_id>")
        return

    # 3. Call service
    try:
        result = await my_service.do_something(event_id)
    except EventNotFoundError:
        await update.effective_message.reply_text("❌ Мероприятие не найдено.")
        return

    # 4. Respond to user
    await update.effective_message.reply_html(f"✅ Готово: {result}")

    # 5. Log action
    await audit_service.log_action(event_id, "my_action", update.effective_user.id)
```

### Example Service

```python
async def do_something(event_id: str) -> dict:
    """Description of what this function does.

    Args:
        event_id: UUID of the event

    Returns:
        Dict with result data

    Raises:
        EventNotFoundError: If event doesn't exist
        DatabaseError: If query fails
    """
    try:
        db = get_db()
        result = db.table("events").select("*").eq("event_id", event_id).execute()

        if not result.data:
            raise EventNotFoundError(f"Event {event_id} not found")

        return result.data[0]
    except EventNotFoundError:
        raise
    except Exception as e:
        logger.error(f"do_something error: {e}")
        raise DatabaseError(f"Database error: {e}")
```

### Type Hints

Use type hints for all function signatures:

```python
from typing import Optional, List, Dict

async def get_applicants(
    event_id: str,
    status: Optional[ApplicationStatus] = None
) -> List[Dict]:
    ...
```

### Logging

Use appropriate log levels:

```python
import logging
logger = logging.getLogger(__name__)

logger.debug("Detailed debug info")      # DEBUG: Variable values, loop iterations
logger.info("Normal operation")           # INFO: Handler started, action completed
logger.warning("Recoverable issue")       # WARNING: Failed to send message to one user
logger.error("Serious error")             # ERROR: Database query failed, exception caught
```

---

## Adding New Features

### Adding a New Command

1. **Create handler function** in appropriate file (e.g., `handlers/admin_handler.py`):

```python
async def my_new_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/my_new_command — Description."""
    # Implementation
    await update.effective_message.reply_text("Done!")
```

2. **Register in `main.py`**:

```python
from handlers.admin_handler import my_new_cmd

# In main():
app.add_handler(CommandHandler("my_new_command", my_new_cmd))
```

3. **Update documentation**:
   - Add to README.md command tables
   - Update relevant handler doc

---

### Adding a New Callback Action

1. **Add callback handler** or extend existing one:

```python
async def handle_my_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    action, event_id = query.data.split(":")[1:]
    # Implementation
```

2. **Register pattern in `main.py`**:

```python
app.add_handler(
    CallbackQueryHandler(handle_my_callback, pattern=r"^my_action:")
)
```

3. **Create button** in keyboard builder (`utils/keyboards.py`):

```python
InlineKeyboardButton("My Action", callback_data=f"my_action:{event_id}")
```

---

### Adding a New ConversationHandler

1. **Define states** (usually at top of handler file):

```python
STATE_ONE, STATE_TWO, STATE_THREE = range(3)
```

2. **Create handler functions**:

```python
async def start_conv(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Step 1: Input something")
    return STATE_ONE

async def handle_state_one(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["value"] = update.message.text
    await update.message.reply_text("Step 2: Input more")
    return STATE_TWO

async def handle_state_two(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Process data
    await update.message.reply_text("Done!")
    return ConversationHandler.END
```

3. **Build ConversationHandler**:

```python
def get_my_conversation_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("my_conv", start_conv)],
        states={
            STATE_ONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_state_one)],
            STATE_TWO: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_state_two)],
        },
        fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)],
        allow_reentry=True,
        name="my_conversation",
        persistent=False
    )
```

4. **Register in `main.py`**:

```python
from handlers.my_handler import get_my_conversation_handler

app.add_handler(get_my_conversation_handler())
```

---

### Adding a New Service

1. **Create file** in `services/` (e.g., `services/notification_service.py`)

2. **Implement functions**:

```python
import logging
from database import get_db
from utils.exceptions import DatabaseError

logger = logging.getLogger(__name__)

async def send_notification(user_id: int, message: str) -> bool:
    """Send notification to user."""
    try:
        # Implementation
        return True
    except Exception as e:
        logger.error(f"send_notification error: {e}")
        raise DatabaseError(f"Notification error: {e}")
```

3. **Export in `services/__init__.py`** (optional, for cleaner imports):

```python
from . import notification_service
```

4. **Use in handler**:

```python
from services import notification_service

await notification_service.send_notification(user_id, "Hello!")
```

---

### Adding a New Model

1. **Create file** in `models/` (e.g., `models/payment.py`)

2. **Define Pydantic model**:

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class Payment(BaseModel):
    payment_id: Optional[str] = None
    event_id: str
    amount: float
    status: str = "pending"
    created_at: Optional[datetime] = None
```

3. **Add to database schema** (`supabase_schema.sql`):

```sql
CREATE TABLE IF NOT EXISTS payments (
    payment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id UUID REFERENCES events(event_id) ON DELETE CASCADE,
    amount NUMERIC NOT NULL,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT now()
);
```

4. **Create service functions** to interact with table

---

## Database Migrations

### Adding a Column

1. **Update Supabase schema**:

```sql
ALTER TABLE events ADD COLUMN channel_chat_id BIGINT;
ALTER TABLE events ADD COLUMN channel_message_id BIGINT;
```

2. **Update Pydantic model**:

```python
class Event(BaseModel):
    channel_chat_id: Optional[str] = None
    channel_message_id: Optional[str] = None
```

3. **Update service functions** that create/update the table:

```python
data = {
    # ... existing fields
    "channel_chat_id": event.channel_chat_id,
    "channel_message_id": event.channel_message_id,
}
```

4. **Document the change** in CHANGELOG.md

### Creating a New Table

1. Add `CREATE TABLE` statement to `supabase_schema.sql`
2. Add indexes for performance
3. Add RLS policies if needed
4. Create Pydantic model
5. Create service functions

---

## Testing

### Manual Testing Checklist

Before deploying:

- [ ] Bot starts without errors
- [ ] All commands respond correctly
- [ ] Conversation flows complete without hanging
- [ ] Database queries return expected results
- [ ] Error messages are user-friendly
- [ ] Permissions enforced (recruiters can't access other companies)
- [ ] Scheduler tasks execute at correct times

### Unit Testing (Future)

When test framework is added:

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_event_service.py

# Run with coverage
pytest --cov=services --cov=handlers
```

---

## Debugging

### Enable Debug Logging

Set in `.env`:

```env
LOG_LEVEL=DEBUG
```

### Common Issues

#### Handler Not Triggered

**Check:**
1. Handler registered in `main.py`?
2. Pattern regex matches callback data?
3. No other handler catching it first (priority/order matters)?

#### Database Query Fails

**Check:**
1. Table/column names correct?
2. RLS policies allow access?
3. Using service_role key (not anon key)?

#### ConversationHandler Stuck

**Check:**
1. State returned correctly (`return STATE_NAME`)?
2. Fallback handler registered?
3. `context.user_data` not cleared prematurely?

#### Scheduler Not Running

**Check:**
1. `get_scheduler_async()` called in `on_startup`?
2. Timezone correct?
3. Bot has permission to message recipients?

### Using Python Debugger

```python
import pdb; pdb.set_trace()  # Breakpoint
```

Or use VS Code debugger:

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: Current File",
            "type": "python",
            "request": "launch",
            "program": "${file}",
            "console": "integratedTerminal"
        }
    ]
}
```

---

## Deployment

### Production Checklist

- [ ] `.env` configured with production values
- [ ] `LOG_LEVEL=INFO` or `WARNING` (not `DEBUG`)
- [ ] Supabase using production database
- [ ] Google credentials file in place (if using Sheets)
- [ ] Bot token is production bot (not test bot)
- [ ] `SUPER_ADMIN_ID` set correctly
- [ ] Process manager configured (systemd, pm2, Docker)

### Running as Background Service

#### Linux (systemd)

Create `/etc/systemd/system/nexus-bot.service`:

```ini
[Unit]
Description=Nexus AI Telegram Bot
After=network.target

[Service]
Type=simple
User=botuser
WorkingDirectory=/opt/nexus_for_waiters
ExecStart=/opt/nexus_for_waiters/.venv/bin/python main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable nexus-bot
sudo systemctl start nexus-bot
sudo systemctl status nexus-bot
```

#### Windows (Task Scheduler)

1. Open Task Scheduler
2. Create Basic Task
3. Trigger: At startup
4. Action: Start a program
   - Program: `python.exe`
   - Arguments: `main.py`
   - Start in: `d:\nexus_for_waiters`

#### Docker (Optional)

Create `Dockerfile`:

```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]
```

Build and run:

```bash
docker build -t nexus-bot .
docker run -d --env-file .env --name nexus-bot nexus-bot
```

### Monitoring

- Check logs regularly: `journalctl -u nexus-bot -f` (Linux)
- Monitor Supabase usage and query performance
- Set up error notifications (e.g., Sentry, Telegram alerts)

---

## Git Workflow

### Branch Strategy

- **`main`**: Production-ready code
- **`develop`**: Integration branch for features
- **`feature/<name>`**: New features
- **`fix/<name>`**: Bug fixes
- **`hotfix/<name>`**: Urgent production fixes

### Commit Messages

Use conventional commits format:

```
<type>(<scope>): <description>

[optional body]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `test`: Test additions/changes
- `chore`: Maintenance tasks

**Examples:**

```
feat(handlers): add /close_event command with post update

fix(services): handle media caption in edit_message_text

docs(readme): update architecture diagram

refactor(models): consolidate deprecated fields in EventCandidate
```

### Pull Request Process

1. Create feature branch from `develop`
2. Implement changes
3. Test manually (run bot, test all affected flows)
4. Update documentation if needed
5. Create PR with description of changes
6. Request review
7. Merge to `develop`
8. Deploy and test in staging
9. Merge `develop` to `main` for release

---

[← Back to README](README.md)
