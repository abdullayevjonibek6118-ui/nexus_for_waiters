"""
Nexus AI — Handler: Кандидаты
Команды: /voters, /select_candidates, /set_times, /notify_candidates
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes
from config import settings
from models.event import EventStatus
from services import event_service, candidate_service, audit_service, recruiter_service
from utils.keyboards import get_candidate_select_keyboard, get_confirm_keyboard, get_set_times_keyboard
from utils.validators import validate_time_format

logger = logging.getLogger(__name__)


async def is_recruiter(user_id: int) -> bool:
    """Проверка прав: Владелец или Рекрутер."""
    if user_id == settings.super_admin_id:
        return True
    return await recruiter_service.is_recruiter(user_id)


async def list_voters(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/voters <event_id> — Список всех проголосовавших."""
    if not await is_recruiter(update.effective_user.id):
        await update.effective_message.reply_text("⛔ У вас нет прав.")
        return
    if not context.args:
        await update.effective_message.reply_text("Использование: /voters <event_id>")
        return

    event_id = context.args[0]
    voters = await candidate_service.get_voters(event_id)
    if not voters:
        await update.effective_message.reply_text("📭 Никто ещё не проголосовал.")
        return

    text = f"👥 <b>Проголосовавшие ({len(voters)}):</b>\n\n"
    for v in voters:
        p = v.get("candidates", {}) or {}
        name = f"{p.get('first_name','?')} {p.get('last_name','')}".strip()
        vote_emoji = {"yes": "✅", "maybe": "🤔", "no": "❌"}.get(v.get("vote_status",""), "❓")
        tg = p.get("telegram_username", "")
        text += f"{vote_emoji} {name}"
        if tg:
            text += f" (@{tg})"
        text += "\n"

    await update.effective_message.reply_html(text)


async def select_candidates_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/select_candidates <event_id> — Интерактивный выбор кандидатов."""
    if not await is_recruiter(update.effective_user.id):
        await update.effective_message.reply_text("⛔ У вас нет прав.")
        return
    if not context.args:
        await update.effective_message.reply_text("Использование: /select_candidates <event_id>")
        return

    event_id = context.args[0]
    voters = await candidate_service.get_voters(event_id)
    if not voters:
        await update.effective_message.reply_text("📭 Нет проголосовавших для выбора.")
        return

    # Сохраним список выбранных в context
    context.user_data["selecting_event"] = event_id
    context.user_data["pending_selected"] = set()

    await update.effective_message.reply_html(
        f"👥 <b>Выберите кандидатов</b> для мероприятия:\n"
        f"Нажмите на имя, чтобы отметить. Затем «Сохранить выбор».",
        reply_markup=get_candidate_select_keyboard(voters, event_id),
    )


async def handle_toggle_select(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Callback: переключение выбора кандидата."""
    query = update.callback_query
    await query.answer()
    _, event_id, user_id_str = query.data.split(":")
    user_id = int(user_id_str)

    pending = context.user_data.get("pending_selected", set())
    if user_id in pending:
        pending.discard(user_id)
        await query.answer("❌ Кандидат снят с выбора")
    else:
        pending.add(user_id)
        await query.answer("✅ Кандидат отмечен")
    context.user_data["pending_selected"] = pending


async def handle_save_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Callback: сохранение выбранных кандидатов."""
    query = update.callback_query
    await query.answer()
    _, event_id = query.data.split(":")

    selected_ids = context.user_data.get("pending_selected", set())
    if not selected_ids:
        await query.edit_message_text("❌ Никто не выбран.")
        return

    await candidate_service.reset_event_selections(event_id)
    for uid in selected_ids:
        await candidate_service.select_candidate(event_id, uid, True)

    await event_service.update_event_status(event_id, EventStatus.SELECTION_COMPLETED)
    await audit_service.log_action(
        event_id, "candidates_selected", query.from_user.id,
        {"selected_ids": list(selected_ids)}
    )

    await query.edit_message_text(
        f"✅ Выбрано <b>{len(selected_ids)}</b> кандидатов!\n"
        f"Статус мероприятия: Selection_Completed\n\n"
        f"Теперь используйте /set_times {event_id}",
        parse_mode="HTML",
    )
    context.user_data.pop("pending_selected", None)


async def set_times_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /set_times <event_id>
    Показывает выбранных кандидатов и просит указать времена.
    Формат: /set_times <event_id> <user_id> <HH:MM> <HH:MM>
    """
    if not await is_recruiter(update.effective_user.id):
        await update.effective_message.reply_text("⛔ У вас нет прав.")
        return
    if not context.args:
        await update.effective_message.reply_text("Использование: /set_times <event_id>")
        return

    event_id = context.args[0]

    # Если переданы полные аргументы: /set_times <event_id> <user_id> <arrival> <departure>
    if len(context.args) == 4:
        _, uid_str, arrival, departure = context.args
        if not validate_time_format(arrival) or not validate_time_format(departure):
            await update.effective_message.reply_text("❌ Неверный формат времени. Используйте HH:MM (например: 09:00 18:00)")
            return

        await candidate_service.set_arrival_departure(event_id, int(uid_str), arrival, departure)
        await update.effective_message.reply_html(
            f"✅ Время назначено:\n"
            f"Кандидат ID <code>{uid_str}</code>\n"
            f"🟢 Приход: {arrival} | 🔴 Уход: {departure}"
        )
        return

    # Показать список выбранных кандидатов
    selected = await candidate_service.get_selected_candidates(event_id)
    if not selected:
        await update.effective_message.reply_text("❌ Нет выбранных кандидатов.")
        return

    text = (
        f"⏰ <b>Назначение времени для мероприятия</b>\n\n"
        f"Выберите кандидата, чтобы назначить ему время,\n"
        f"или нажмите «Назначить всем одинаковое время».\n\n"
        f"<b>Текущие времена:</b>\n"
    )
    for c in selected:
        p = c.get("candidates", {}) or {}
        name = f"{p.get('first_name','?')} {p.get('last_name','')}".strip()
        arrival = c.get("arrival_time", "—")
        departure = c.get("departure_time", "—")
        text += f"👤 {name}: 🟢 {arrival} → 🔴 {departure}\n"

    await update.effective_message.reply_html(
        text,
        reply_markup=get_set_times_keyboard(selected, event_id)
    )


async def handle_set_time_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка кнопок выбора кандидата для времени."""
    query = update.callback_query
    await query.answer()
    
    data = query.data.split(":")
    action = data[0] # st_all or st_one
    event_id = data[1]
    
    if action == "st_all":
        context.user_data["st_state"] = {"event_id": event_id, "mode": "all"}
        await query.edit_message_text(
            "⏳ Введите время для <b>всех</b> кандидатов в формате:\n<code>HH:MM HH:MM</code>\n\nПример: <code>09:00 20:00</code>",
            parse_mode="HTML"
        )
    elif action == "st_one":
        user_id = int(data[2])
        context.user_data["st_state"] = {"event_id": event_id, "mode": "one", "user_id": user_id}
        await query.edit_message_text(
            f"⏳ Введите время для кандидата (ID: {user_id}) в формате:\n<code>HH:MM HH:MM</code>",
            parse_mode="HTML"
        )


async def handle_time_message_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка текстового ввода времени после нажатия кнопок."""
    state = context.user_data.get("st_state")
    if not state:
        return # Не в состоянии ожидания времени - игнорируем
    
    text = update.message.text.strip()
    parts = text.split()
    if len(parts) != 2:
        await update.message.reply_text("❌ Ошибка. Введите два значения времени через пробел: HH:MM HH:MM")
        return
        
    arrival, departure = parts
    if not validate_time_format(arrival) or not validate_time_format(departure):
        await update.message.reply_text("❌ Неверный формат. Используйте HH:MM HH:MM (например, 09:00 18:00)")
        return
        
    event_id = state["event_id"]
    
    if state["mode"] == "all":
        selected = await candidate_service.get_selected_candidates(event_id)
        for c in selected:
            await candidate_service.set_arrival_departure(event_id, c["user_id"], arrival, departure)
        await update.message.reply_html(f"✅ Время <b>{arrival} – {departure}</b> назначено <b>всем</b> кандидатам!")
    
    elif state["mode"] == "one":
        user_id = state["user_id"]
        await candidate_service.set_arrival_departure(event_id, user_id, arrival, departure)
        await update.message.reply_html(f"✅ Время <b>{arrival} – {departure}</b> назначено для ID <code>{user_id}</code>")

    # Очищаем состояние и предлагаем вернуться к списку
    context.user_data.pop("st_state")
    await set_times_cmd(update, context) # Повторно вызываем команду, чтобы показать обновленный список


async def notify_candidates_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /notify_candidates <event_id>
    Отправляет приватные сообщения выбранным кандидатам с деталями мероприятия.
    """
    if not await is_recruiter(update.effective_user.id):
        await update.effective_message.reply_text("⛔ У вас нет прав.")
        return
    if not context.args:
        await update.effective_message.reply_text("Использование: /notify_candidates <event_id>")
        return

    event_id = context.args[0]
    event = await event_service.get_event(event_id)
    if not event:
        await update.effective_message.reply_text("❌ Мероприятие не найдено.")
        return

    selected = await candidate_service.get_selected_candidates(event_id)
    if not selected:
        await update.effective_message.reply_text("❌ Нет выбранных кандидатов.")
        return

    sent, failed = 0, 0
    for c in selected:
        p = c.get("candidates", {}) or {}
        user_id = c.get("user_id")
        name = p.get("first_name", "")
        arrival = c.get("arrival_time", "уточняется")
        departure = c.get("departure_time", "уточняется")

        msg = (
            f"🎉 <b>Вы выбраны на мероприятие!</b>\n\n"
            f"📌 <b>{event.title}</b>\n"
            f"📅 Дата: {event.date}\n"
            f"📍 Место: {event.location}\n"
            f"⏰ Ваше время: {arrival} – {departure}\n\n"
            f"Пожалуйста, подтвердите участие:"
        )
        try:
            await context.bot.send_message(
                chat_id=user_id, text=msg, parse_mode="HTML",
                reply_markup=get_confirm_keyboard(event_id),
            )
            sent += 1
        except Exception as e:
            logger.warning(f"Не удалось отправить сообщение {user_id}: {e}")
            failed += 1

    await event_service.update_event_status(event_id, EventStatus.CANDIDATES_CONFIRMED)
    await audit_service.log_action(
        event_id, "candidates_notified", update.effective_user.id,
        {"sent": sent, "failed": failed}
    )

    await update.effective_message.reply_html(
        f"✅ Уведомления отправлены!\n"
        f"📤 Доставлено: <b>{sent}</b> | ❌ Не доставлено: <b>{failed}</b>"
    )


async def handle_candidate_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Callback: кандидат подтверждает/отклоняет участие."""
    query = update.callback_query
    await query.answer()
    action, event_id = query.data.split(":")
    user = query.from_user

    if action == "confirm_yes":
        await candidate_service.confirm_candidate(event_id, user.id)
        await query.edit_message_text(
            f"✅ <b>Участие подтверждено!</b>\n\n"
            f"Спасибо, {user.first_name}! Ждём вас на мероприятии.",
            parse_mode="HTML",
        )
        await audit_service.log_action(event_id, "candidate_confirmed", user.id, {})
    else:
        await query.edit_message_text(
            f"❌ Вы отказались от участия. Спасибо за ответ, {user.first_name}.",
            parse_mode="HTML",
        )
        await audit_service.log_action(event_id, "candidate_declined", user.id, {})


async def handle_set_gender(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Callback: сохранение пола кандидата при регистрации."""
    query = update.callback_query
    await query.answer()
    _, gender = query.data.split(":")
    user = query.from_user

    # Сначала создадим профиль, если его еще нет (у нас есть только user info из бота)
    await candidate_service.get_or_create_candidate(
        user_id=user.id,
        first_name=user.first_name or "—",
        last_name=user.last_name,
        username=user.username,
    )

    await candidate_service.update_gender(user.id, gender)
    
    gender_text = "Мужской" if gender == "Male" else "Женский"
    await query.edit_message_text(
        f"✅ Ваш пол сохранён: <b>{gender_text}</b>.\n\n"
        f"Теперь вы зарегистрированы! Пожалуйста, поделитесь своим контактом кнопкой ниже, "
        f"чтобы рекрутер мог связаться с вами.",
        parse_mode="HTML"
    )
    
    from telegram import ReplyKeyboardMarkup, KeyboardButton
    keyboard = [[KeyboardButton("📞 Поделиться контактом", request_contact=True)]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await context.bot.send_message(
        chat_id=user.id,
        text="Нажмите кнопку ниже, чтобы отправить номер телефона:",
        reply_markup=reply_markup
    )


async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка отправленного контакта от кандидата."""
    contact = update.message.contact
    user = update.effective_user
    if contact and contact.user_id == user.id:
        phone = contact.phone_number
        await candidate_service.update_phone_number(user.id, phone)
        
        from telegram import ReplyKeyboardRemove
        await update.effective_message.reply_html(
            f"✅ <b>Спасибо!</b> Ваш номер телефона (<code>{phone}</code>) сохранён.\n"
            f"Теперь рекрутер сможет с вами связаться при необходимости.",
            reply_markup=ReplyKeyboardRemove()
        )
    else:
        await update.effective_message.reply_text("Пожалуйста, отправьте именно свой контакт, используя кнопку в меню.")

