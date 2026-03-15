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
    CallbackQueryHandler,
    filters,
)
from config import settings
from models.event import Event
from services import event_service, audit_service, recruiter_service, candidate_service
from utils.keyboards import get_event_keyboard
from utils.validators import validate_date_format, validate_max_candidates

logger = logging.getLogger(__name__)

# Состояния ConversationHandler
E_TITLE, E_DATE, E_LOC, E_PAYMENT, E_MAX, E_GENDERS, E_ROLES, E_TIMES = range(8)



# Маппинг русских месяцев → ISO-номер
_MONTHS_RU = {
    "январь": 1, "января": 1,
    "февраль": 2, "февраля": 2,
    "март": 3, "марта": 3,
    "апрель": 4, "апреля": 4,
    "май": 5, "мая": 5,
    "июнь": 6, "июня": 6,
    "июль": 7, "июля": 7,
    "август": 8, "августа": 8,
    "сентябрь": 9, "сентября": 9,
    "октябрь": 10, "октября": 10,
    "ноябрь": 11, "ноября": 11,
    "декабрь": 12, "декабря": 12,
}

def parse_russian_date(text: str) -> str | None:
    """Конвертирует русскую дату в формат YYYY-MM-DD для Supabase.
    Принимает: '15 апреля', '15 апреля 2026', '2026-04-15', '15.04.2026'
    """
    import datetime
    text = text.strip().lower()
    current_year = datetime.date.today().year

    # Уже в ISO формате: 2026-04-15
    try:
        return str(datetime.date.fromisoformat(text))
    except ValueError:
        pass

    # Формат DD.MM.YYYY
    try:
        return str(datetime.datetime.strptime(text, "%d.%m.%Y").date())
    except ValueError:
        pass

    # Русский формат: '15 апреля' или '15 апреля 2026'
    parts = text.split()
    if len(parts) >= 2:
        try:
            day = int(parts[0])
            month = _MONTHS_RU.get(parts[1])
            year = int(parts[2]) if len(parts) >= 3 else current_year
            if month:
                return str(datetime.date(year, month, day))
        except (ValueError, IndexError):
            pass

    return None  # Формат не распознан


async def is_recruiter(user_id: int) -> bool:
    """Проверка, является ли пользователь рекрутером или владельцем."""
    if user_id == settings.super_admin_id:
        return True
    return await recruiter_service.is_recruiter(user_id)


# ─── /create_event ──────────────────────────────────────────────────────────

# ─── /events Dashboard (Этап 1) ───────────────────────────────────────────────

async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена текущего диалога."""
    await update.message.reply_text("❌ Действие отменено.")
    context.user_data.clear()
    return ConversationHandler.END


async def events_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/events — Главная панель рекрутера."""
    if not await is_recruiter(update.effective_user.id):
        await update.message.reply_text("⛔ У вас нет прав.")
        return

    from utils.keyboards import get_recruiter_dashboard_keyboard
    text = (
        "💼 <b>Панель управления мероприятиями</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Здесь вы можете планировать новые события, управлять активными наборами и просматривать отчеты.\n\n"
        "✨ <i>Выберите действие ниже:</i>"
    )
    await update.message.reply_html(
        text,
        reply_markup=get_recruiter_dashboard_keyboard()
    )

# ─── /create_event (Этап 2) ──────────────────────────────────────────────────

async def create_event_start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Команда /create_event или нажатие кнопки."""
    if update.callback_query:
        await update.callback_query.answer()
        send = update.callback_query.message.reply_text
    else:
        if not await is_recruiter(update.effective_user.id):
            return ConversationHandler.END
        send = update.message.reply_text  # используем reply_text везде

    await send(
        "📝 <b>Шаг 1 из 8: Название</b>\n\nВведите название мероприятия:",
        parse_mode="HTML"
    )
    return E_TITLE

async def handle_ev_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["ev_name"] = update.message.text.strip()
    await update.message.reply_html(
        "📅 <b>Шаг 2 из 8: Дата</b>\n\n"
        "Введите дату мероприятия.\n"
        "<i>Примеры: <code>15 апреля</code>, <code>15 апреля 2026</code>, <code>15.04.2026</code></i>"
    )
    return E_DATE

async def handle_ev_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    raw = update.message.text.strip()
    iso_date = parse_russian_date(raw)
    if not iso_date:
        await update.message.reply_html(
            "❌ <b>Не удалось распознать дату.</b>\n\n"
            "Пожалуйста, введите дату в одном из форматов:\n"
            "• <code>15 апреля</code>\n"
            "• <code>15 апреля 2026</code>\n"
            "• <code>15.04.2026</code>"
        )
        return E_DATE
    context.user_data["ev_date"] = iso_date
    await update.message.reply_html("📍 <b>Шаг 3 из 8: Место проведения</b>\n\nУкажите точный адрес или заведение:")
    return E_LOC

async def handle_ev_loc(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["ev_loc"] = update.message.text.strip()
    await update.message.reply_html("💰 <b>Шаг 4 из 8: Оплата</b>\n\nУкажите сумму оплаты (например: 4000 или 350-400/час):")
    return E_PAYMENT

async def handle_ev_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    payment_raw = update.message.text.strip()
    # Добавляем знак ₽ если его нет
    if "₽" not in payment_raw and "руб" not in payment_raw.lower():
        payment_raw = f"{payment_raw} ₽"
    context.user_data["ev_payment"] = payment_raw
    await update.message.reply_html("👥 <b>Шаг 5 из 8: Количество сотрудников</b>\n\nСколько всего человек нужно на мероприятие?")
    return E_MAX

async def handle_ev_max(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        max_c = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("❌ Введите число!")
        return E_MAX
    
    context.user_data["ev_max"] = max_c
    await update.message.reply_html(
        "🚻 <b>Шаг 6 из 8: Требования к полу</b>\n\n"
        "Сколько нужно парней и девушек?\n"
        "<i>Например: <code>М-5 Ж-5</code> или введите <code>0</code> если пол не важен.</i>"
    )
    return E_GENDERS

async def handle_ev_genders(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip().lower()
    men = 0
    women = 0
    
    if text != "0":
        import re
        men_match = re.search(r'м[ -]?(\d+)', text)
        women_match = re.search(r'ж[ -]?(\d+)', text)
        if men_match: men = int(men_match.group(1))
        if women_match: women = int(women_match.group(1))
        
    context.user_data["ev_men"] = men
    context.user_data["ev_women"] = women

    await update.message.reply_html("🎭 <b>Шаг 7 из 8: Роли</b>\n\nКакие роли нужны? (через запятую)\n<i>Пример: Промоутер, Хостес, Регистратор</i>")
    return E_ROLES

async def handle_ev_roles(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    roles = [r.strip() for r in update.message.text.split(",")]
    context.user_data["ev_roles"] = roles
    await update.message.reply_html("⏰ <b>Шаг 8 из 8: Времена прихода</b>\n\nВведите доступные времена через запятую:\n<i>Пример: 08:00, 09:00, 10:00</i>")
    return E_TIMES

async def handle_ev_times(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    times = [t.strip() for t in update.message.text.split(",")]
    context.user_data["ev_times"] = times
    
    user = update.effective_user
    rec_profile = await recruiter_service.get_recruiter(user.id)
    company_id = rec_profile["company_id"] if rec_profile else None

    event = Event(
        title=context.user_data["ev_name"],
        date=context.user_data["ev_date"],
        location=context.user_data.get("ev_loc", "Москва"),
        payment=context.user_data.get("ev_payment"),
        max_candidates=context.user_data["ev_max"],
        required_roles=context.user_data["ev_roles"],
        arrival_times=context.user_data["ev_times"],
        required_men=context.user_data.get("ev_men", 0),
        required_women=context.user_data.get("ev_women", 0),
        company_id=company_id,
        created_by=user.id
    )

    saved = await event_service.create_event(event)
    if saved:
        context.user_data["selected_event_id"] = saved.event_id
        from utils.keyboards import get_event_post_creation_keyboard
        roles_str = ", ".join(context.user_data["ev_roles"])
        times_str = ", ".join(context.user_data["ev_times"])
        
        gender_req = ""
        if saved.required_men > 0 or saved.required_women > 0:
            gender_req = f"\n🚻 <b>Пол:</b> М-{saved.required_men} Ж-{saved.required_women}"

        text = (
            "✅ <b>Мероприятие создано!</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📌 <b>Название:</b> {saved.title}\n"
            f"📅 <b>Дата:</b> {saved.date}\n"
            f"📍 <b>Адрес:</b> {saved.location}\n"
            f"💰 <b>Оплата:</b> {saved.payment}\n"
            f"👥 <b>Лимит:</b> {saved.max_candidates} чел.{gender_req}\n"
            f"🎭 <b>Роли:</b> {roles_str}\n"
            f"⏰ <b>Времена:</b> {times_str}\n\n"
            "<i>Что делаем дальше?</i>"
        )
        await update.message.reply_html(
            text,
            reply_markup=get_event_post_creation_keyboard()
        )
    else:
        await update.message.reply_text("❌ Ошибка при создании мероприятия. Попробуйте снова.")

    return ConversationHandler.END


# ─── /list_events ────────────────────────────────────────────────────────────

async def list_events(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показать список активных мероприятий как Reply-кнопки."""
    user_id = update.effective_user.id

    if not await is_recruiter(user_id):
        await update.effective_message.reply_text("⛔ У вас нет прав.")
        return

    rec_profile = await recruiter_service.get_recruiter(user_id)
    company_id = rec_profile["company_id"] if rec_profile else None
    events = await event_service.get_active_events(company_id=company_id)
    
    if not events:
        await update.effective_message.reply_html("📭 <b>У вас пока нет активных мероприятий.</b>")
        return

    # Сохраняем список мероприятий для последующего поиска по названию на кнопке
    context.user_data["ev_list"] = {f"📅 {ev.date} | {ev.title}": ev.event_id for ev in events}

    text = (
        "📅 <b>Ваши активные мероприятия</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "<i>Выберите проект из списка ниже:</i>"
    )
    from utils.keyboards import get_events_list_reply_keyboard
    await update.effective_message.reply_html(
        text, 
        reply_markup=get_events_list_reply_keyboard(events)
    )


async def handle_recruiter_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик главного меню рекрутера (Reply-кнопки)."""
    text = update.message.text
    
    if text == "🆕 Создать мероприятие":
        # Команда /create_event теперь поймается ConversationHandler напрямую
        # Если вдруг нет (например, стейт сбросился), вызываем стартовую логику:
        await create_event_start_cmd(update, context)
    elif text == "📋 Мои мероприятия":
        await list_events(update, context)
    elif text == "📊 Отчеты":
        # Используем существующую логику отчетов, но адаптированную под Reply
        user_id = update.effective_user.id
        rec_profile = await recruiter_service.get_recruiter(user_id)
        company_id = rec_profile.get("company_id") if rec_profile else None
        events = await event_service.get_active_events(company_id=company_id)
        
        report_text = (
            "📊 <b>Статистика и отчеты</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📅 <b>Активных проектов (мероприятий):</b> {len(events)}\n\n"
            "<i>💡 Чтобы получить отчет, выберите мероприятие в списке и нажмите «📄 Экспорт Excel».</i>"
        )
        await update.message.reply_html(report_text)
    elif text == "❓ Помощь":
        await update.message.reply_html("ℹ️ <b>Справка:</b>\n\nИспользуйте кнопки меню для управления проектами.")


async def handle_event_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик выбора конкретного мероприятия из списка (Reply-кнопки)."""
    text = update.message.text
    ev_list = context.user_data.get("ev_list", {})
    
    if text in ev_list:
        event_id = ev_list[text]
        await show_event_management_menu(update, context, event_id)
    elif text == "⬅️ Назад в меню":
        await events_dashboard(update, context)


async def show_event_management_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, event_id: str) -> None:
    """Хелпер: показать меню управления мероприятием."""
    context.user_data["selected_event_id"] = event_id
    event = await event_service.get_event(event_id)
    
    if not event:
        await update.effective_message.reply_text("❌ Мероприятие не найдено.")
        return

    from utils.keyboards import get_event_action_reply_keyboard
    info = (
        f"⚙️ <b>Управление: {event.title}</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📅 <b>Дата:</b> {event.date}\n"
        f"📍 <b>Место:</b> {event.location}\n"
        f"👥 <b>Лимит:</b> {event.max_candidates}\n"
        f"📊 <b>Статус:</b> {event.status.value}\n\n"
        "<i>Выберите действие для этого мероприятия:</i>"
    )
    await update.effective_message.reply_html(info, reply_markup=get_event_action_reply_keyboard(event.title))


async def handle_event_menu_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик действий внутри меню мероприятия."""
    text = update.message.text
    event_id = context.user_data.get("selected_event_id")
    
    if not event_id and text != "⬅️ К списку мероприятий":
        await update.message.reply_html(
            "⚠️ <b>Сессия истекла или бот был перезагружен.</b>\n\n"
            "Пожалуйста, выберите мероприятие заново из списка через /events."
        )
        return

    if text == "📢 Опубликовать":
        from handlers.poll_handler import publish_poll
        context.args = [event_id]
        await publish_poll(update, context)
    
    elif text == "👥 Карточки":
        from handlers.candidate_handler import show_candidate_cards
        await show_candidate_cards(update, context, event_id=event_id)

    elif text == "✉️ Уведомить":
        from handlers.candidate_handler import notify_candidates_cmd
        context.args = [event_id]
        await notify_candidates_cmd(update, context)

    elif text == "📄 Экспорт Excel":
        from handlers.admin_handler import export_excel_cmd
        context.args = [event_id]
        await export_excel_cmd(update, context)

    elif text == "⏰ Назначить время":
        from handlers.candidate_handler import set_times_cmd
        context.args = [event_id]
        await set_times_cmd(update, context)

    elif text == "🤖 Автоотбор":
        from handlers.candidate_handler import auto_select_cmd
        context.args = [event_id]
        await auto_select_cmd(update, context)

    elif text == "📊 Логи":
        from handlers.admin_handler import logs_cmd
        context.args = [event_id]
        await logs_cmd(update, context)

    elif text == "❌ Архивировать":
        from handlers.admin_handler import close_event_cmd
        context.args = [event_id]
        await close_event_cmd(update, context)

    elif text == "⬅️ К списку мероприятий":
        await list_events(update, context)


# ─── ConversationHandler ─────────────────────────────────────────────────────

def get_create_event_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CommandHandler("create_event", create_event_start_cmd),
            CallbackQueryHandler(create_event_start_cmd, pattern="^ev_create$"),
            MessageHandler(filters.Regex(r"^🆕 Создать мероприятие$"), create_event_start_cmd)
        ],
        states={
            E_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_ev_name)],
            E_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_ev_date)],
            E_LOC: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_ev_loc)],
            E_PAYMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_ev_payment)],
            E_MAX: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_ev_max)],
            E_GENDERS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_ev_genders)],
            E_ROLES: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_ev_roles)],
            E_TIMES: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_ev_times)],
        },
        fallbacks=[CommandHandler("cancel", cancel_conversation)],
        allow_reentry=True,
        name="event_creation",
        persistent=False
    )


async def handle_event_action_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает нажатия в панели рекрутера."""
    query = update.callback_query
    await query.answer()

    data = query.data
    
    if data == "ev_create":
        # Переход в диалог создания (через ConversationHandler)
        # Мы НЕ возвращаем стейт здесь, так как мы вне CH. 
        # Но CallbackQueryHandler в entry_points поймает этот callback и начнет диалог.
        return

    if data == "ev_active":
        await list_events(update, context)
        return

    if data == "ev_reports":
        user_id = update.effective_user.id
        rec_profile = await recruiter_service.get_recruiter(user_id)
        company_id = rec_profile.get("company_id") if rec_profile else None
        events = await event_service.get_active_events(company_id=company_id)
        
        text = (
            "📊 <b>Статистика и отчеты</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📅 <b>Активных проектов (мероприятий):</b> {len(events)}\n\n"
            "<i>💡 Подсказка: Чтобы получить детализированный отчет со списком всех кандидатов, их статусов и времени прихода, "
            "перейдите в раздел «Активные мероприятия», выберите нужное и нажмите кнопку «📄 Excel».</i>"
        )
        from utils.keyboards import get_recruiter_dashboard_keyboard
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=get_recruiter_dashboard_keyboard())
        return

    if ":" not in data: return
    action, event_id = data.split(":")[:2]

    if action == "manage":
        event = await event_service.get_event(event_id)
        if event:
            from utils.keyboards import get_event_post_creation_keyboard
            text = (
                f"📌 <b>{event.title}</b>\n"
                f"📅 Дата: {event.date}\n"
                f"📍 Место: {event.location}\n"
                f"👥 Лимит: {event.max_candidates} чел.\n"
                f"📊 Статус: {event.status.value}"
            )
            await query.message.reply_html(text, reply_markup=get_event_post_creation_keyboard())

    elif action == "ev_publish" or action == "poll_publish":
        from handlers.poll_handler import publish_poll
        context.args = [event_id]
        await publish_poll(update, context)
    
    elif action == "ev_select" or action == "select":
        from handlers.candidate_handler import auto_select_cmd
        context.args = [event_id]
        await auto_select_cmd(update, context)

    elif action == "ev_cands":
        from handlers.candidate_handler import show_candidate_cards
        await show_candidate_cards(update, context, event_id=event_id)

    elif action == "times":
        from handlers.candidate_handler import set_times_cmd
        context.args = [event_id]
        await set_times_cmd(update, context)

    elif action == "notify":
        from handlers.candidate_handler import notify_candidates_cmd
        context.args = [event_id]
        await notify_candidates_cmd(update, context)

    elif action == "logs":
        from handlers.admin_handler import logs_cmd
        context.args = [event_id]
        await logs_cmd(update, context)

    elif action == "export_excel":
        from handlers.admin_handler import export_excel_cmd
        context.args = [event_id]
        await export_excel_cmd(update, context)

    elif action == "sheet":
        from handlers.admin_handler import create_sheet_cmd
        context.args = [event_id]
        await create_sheet_cmd(update, context)

    elif action == "close":
        from handlers.admin_handler import close_event_cmd
        context.args = [event_id]
        await close_event_cmd(update, context)

    elif action == "ev_settings":
        from telegram import InlineKeyboardMarkup, InlineKeyboardButton
        text = (
            "⚙️ <b>Настройки мероприятия</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "В данном разделе скоро появится возможность переименования, изменения времени и лимитов "
            "для активного мероприятия.\n\n"
            "Если вам нужно срочно изменить дату или адрес, пожалуйста, заархивируйте текущее мероприятие и создайте новое."
        )
        markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад к мероприятию", callback_data=f"manage:{event_id}")]])
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=markup)

    elif action == "ev_reports": # В случае если передается как action:id
        text = (
            "📊 <b>Отчет по мероприятию</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Для получения полного списка утвержденных сотрудников и их контактных данных, "
            "воспользуйтесь кнопкой «📄 Excel» или «📋 Google Sheet» в меню управления мероприятием."
        )
        from telegram import InlineKeyboardMarkup, InlineKeyboardButton
        markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data=f"manage:{event_id}")]])
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=markup)

    elif action == "ev_confirm_checkin":
        parts = data.split(":")
        eid = parts[1]
        uid = int(parts[2])
        await candidate_service.confirm_checkin(eid, uid)
        await query.edit_message_text(f"✅ Приход кандидата (ID: {uid}) подтвержден!")

