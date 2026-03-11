"""
Nexus AI — Handler: Создание мероприятий (ConversationHandler)
Команды: /create_event, /list_events
"""
import logging
from telegram import Update, ForceReply
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    filters,
)
from config import settings
from models.event import Event
from services import event_service, audit_service, recruiter_service
from utils.keyboards import get_event_keyboard
from utils.validators import validate_date_format, validate_max_candidates

logger = logging.getLogger(__name__)

# Состояния ConversationHandler
TITLE, DATE, LOCATION, MAX_CANDIDATES, REQUIRED_MEN, REQUIRED_WOMEN = range(6)


async def is_recruiter(user_id: int) -> bool:
    """Проверка, является ли пользователь рекрутером или владельцем."""
    if user_id == settings.super_admin_id:
        return True
    return await recruiter_service.is_recruiter(user_id)


# ─── /create_event ──────────────────────────────────────────────────────────

async def create_event_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало диалога создания мероприятия."""
    user_id = update.effective_user.id
    if not await is_recruiter(user_id):
        await update.message.reply_text("⛔ У вас нет прав для этой команды.")
        return ConversationHandler.END

    await update.message.reply_html(
        "📅 <b>Создание мероприятия</b>\n\n"
        "Шаг 1/4: Введите <b>название</b> мероприятия:",
        reply_markup=ForceReply(selective=True),
    )
    return TITLE


async def event_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["event_title"] = update.message.text.strip()
    await update.message.reply_html(
        "📆 Шаг 2/6: Введите <b>дату</b> мероприятия (формат: DD.MM.YYYY):\n"
        "Пример: 15.03.2026",
        reply_markup=ForceReply(selective=True),
    )
    return DATE


async def event_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    date_str = update.message.text.strip()
    if not validate_date_format(date_str):
        await update.message.reply_text(
            "❌ Неверный формат даты. Введите в формате DD.MM.YYYY (например: 15.03.2026):"
        )
        return DATE

    # Преобразуем в ISO (YYYY-MM-DD) для базы данных
    from datetime import datetime
    iso_date = datetime.strptime(date_str, "%d.%m.%Y").strftime("%Y-%m-%d")
    context.user_data["event_date"] = iso_date
    await update.message.reply_html(
        "📍 Шаг 3/4: Введите <b>место проведения</b>:",
        reply_markup=ForceReply(selective=True),
    )
    return LOCATION


async def event_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["event_location"] = update.message.text.strip()
    await update.message.reply_html(
        "👥 Шаг 4/6: Введите <b>максимальное количество кандидатов</b> (1–100):",
        reply_markup=ForceReply(selective=True),
    )
    return MAX_CANDIDATES


async def event_max_candidates(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    valid, max_c = validate_max_candidates(update.message.text)
    if not valid:
        await update.message.reply_text(
            "❌ Введите целое число от 1 до 100:"
        )
        return MAX_CANDIDATES

    context.user_data["event_max"] = max_c
    await update.message.reply_html(
        "М Шаг 5/6: Введите <b>количество мужчин</b>, необходимых для мероприятия:",
        reply_markup=ForceReply(selective=True),
    )
    return REQUIRED_MEN


async def event_required_men(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        val = int(update.message.text.strip())
        if val < 0: raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Введите положительное целое число:")
        return REQUIRED_MEN

    context.user_data["event_men"] = val
    await update.message.reply_html(
        "Ж Шаг 6/6: Введите <b>количество женщин</b>, необходимых для мероприятия:",
        reply_markup=ForceReply(selective=True),
    )
    return REQUIRED_WOMEN


async def event_required_women(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        val = int(update.message.text.strip())
        if val < 0: raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Введите положительное целое число:")
        return REQUIRED_WOMEN

    context.user_data["event_women"] = val
    max_c = context.user_data["event_max"]
    user = update.effective_user

    # Получаем ID компании рекрутера
    rec_profile = await recruiter_service.get_recruiter(user.id)
    if not rec_profile:
        # Если это владелец, он может создавать мероприятия без компании (или привязать к тестовой), 
        # но обычно мероприятия создают рекрутеры компаний.
        company_id = None
    else:
        company_id = rec_profile["company_id"]

    event = Event(
        title=context.user_data["event_title"],
        company_id=company_id,
        date=context.user_data["event_date"],
        location=context.user_data["event_location"],
        max_candidates=max_c,
        required_men=context.user_data["event_men"],
        required_women=context.user_data["event_women"],
        created_by=user.id,
    )

    saved = await event_service.create_event(event)
    if saved:
        await audit_service.log_action(
            saved.event_id, "event_created", user.id,
            {"title": saved.title, "date": saved.date, "location": saved.location}
        )
        summary = (
            f"✅ <b>Мероприятие создано!</b>\n\n"
            f"🆔 ID: <code>{saved.event_id}</code>\n"
            f"📌 Название: <b>{saved.title}</b>\n"
            f"📅 Дата: {saved.date}\n"
            f"📍 Место: {saved.location}\n"
            f"👥 Лимит: {saved.max_candidates} чел.\n"
            f"М: {saved.required_men} | Ж: {saved.required_women}\n"
            f"📊 Статус: {saved.status.value}"
        )
        await update.message.reply_html(
            summary, reply_markup=get_event_keyboard(saved.event_id)
        )
    else:
        await update.message.reply_text(
            "❌ Ошибка при создании мероприятия. Пожалуйста, попробуйте снова."
        )

    context.user_data.clear()
    return ConversationHandler.END


async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("❌ Создание мероприятия отменено.")
    context.user_data.clear()
    return ConversationHandler.END


# ─── /list_events ────────────────────────────────────────────────────────────

async def list_events(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показать список активных мероприятий."""
    user_id = update.effective_user.id
    if not await is_recruiter(user_id):
        await update.message.reply_text("⛔ У вас нет прав для этой команды.")
        return

    # Получаем компанию рекрутера
    rec_profile = await recruiter_service.get_recruiter(user_id)
    company_id = rec_profile["company_id"] if rec_profile else None

    events = await event_service.get_active_events(company_id=company_id)
    if not events:
        await update.message.reply_text("📭 Нет активных мероприятий.")
        return

    text = "📋 <b>Выберите мероприятие для управления:</b>\n"
    from utils.keyboards import get_events_list_keyboard
    reply_markup = get_events_list_keyboard(events)
    await update.message.reply_html(text, reply_markup=reply_markup)



# ─── ConversationHandler ─────────────────────────────────────────────────────

def get_create_event_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("create_event", create_event_start)],
        states={
            TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, event_title)],
            DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, event_date)],
            LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, event_location)],
            MAX_CANDIDATES: [MessageHandler(filters.TEXT & ~filters.COMMAND, event_max_candidates)],
            REQUIRED_MEN: [MessageHandler(filters.TEXT & ~filters.COMMAND, event_required_men)],
            REQUIRED_WOMEN: [MessageHandler(filters.TEXT & ~filters.COMMAND, event_required_women)],
        },
        fallbacks=[CommandHandler("cancel", cancel_conversation)],
        allow_reentry=True,
    )


async def handle_event_action_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает нажатия на inline-кнопки управления мероприятием."""
    query = update.callback_query
    await query.answer()

    data = query.data
    action, event_id = data.split(":")

    # Имитируем команду
    context.args = [event_id]

    if action == "poll_publish":
        from handlers.poll_handler import publish_poll
        await publish_poll(update, context)
    elif action == "manage":
        event = await event_service.get_event(event_id)
        if event:
            from utils.keyboards import get_event_keyboard
            text = (
                f"📌 <b>{event.title}</b>\n"
                f"🆔 <code>{event.event_id}</code>\n"
                f"📅 Дата: {event.date}\n"
                f"📍 Место: {event.location}\n"
                f"👥 Лимит: {event.max_candidates} чел.\n"
                f"М: {event.required_men} | Ж: {event.required_women}\n"
                f"📊 Статус: {event.status.value}"
            )
            await query.edit_message_text(text, reply_markup=get_event_keyboard(event.event_id), parse_mode="HTML")
    elif action == "select":
        from handlers.candidate_handler import select_candidates_cmd
        await select_candidates_cmd(update, context)
    elif action == "times":
        from handlers.candidate_handler import set_times_cmd
        await set_times_cmd(update, context)
    elif action == "sheet":
        from handlers.admin_handler import create_sheet_cmd
        await create_sheet_cmd(update, context)
    elif action == "notify":
        from handlers.candidate_handler import notify_candidates_cmd
        await notify_candidates_cmd(update, context)
    elif action == "logs":
        from handlers.admin_handler import logs_cmd
        await logs_cmd(update, context)
    elif action == "close":
        from handlers.admin_handler import close_event_cmd
        await close_event_cmd(update, context)
    elif action == "export_excel":
        from handlers.admin_handler import export_excel_cmd
        await export_excel_cmd(update, context)

