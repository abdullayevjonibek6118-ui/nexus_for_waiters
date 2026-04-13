"""
Nexus AI — Handler: Кандидаты
Команды: /voters, /select_candidates, /set_times, /notify_candidates
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes
from config import settings
from utils.constants import ApplicationStatus, EventStatus
from utils.keyboards import (
    get_candidate_select_keyboard, 
    get_confirm_keyboard, 
    get_set_times_keyboard,
    get_candidate_card_keyboard,
    get_invitation_keyboard,
    get_checkin_keyboard
)
from utils.validators import validate_time_format
from services import event_service, candidate_service, audit_service, recruiter_service

logger = logging.getLogger(__name__)


async def is_recruiter(user_id: int) -> bool:
    """Проверка прав: Владелец или Рекрутер."""
    if user_id == settings.super_admin_id:
        return True
    return await recruiter_service.is_recruiter(user_id)


async def list_voters(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/voters <event_id> — Список всех проголосовавших."""
    if not await is_recruiter(update.effective_user.id):
        await update.effective_message.reply_text("⛔ У вас нет прав для этой команды.")
        return
    if not context.args:
        await update.effective_message.reply_text("Использование: /voters <event_id>")
        return

    event_id = context.args[0]
    voters = await candidate_service.get_applicants(event_id)
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
            # Ensure single @ prefix
            tg_formatted = f"@{tg.lstrip('@')}"
            text += f" ({tg_formatted})"
        text += "\n"

    await update.effective_message.reply_html(text)


# ─── Управление кандидатами через карточки (Этап 5) ──────────────────────────

async def show_candidate_cards(update: Update, context: ContextTypes.DEFAULT_TYPE, event_id: str = None) -> None:
    """Отображение карточек кандидатов по очереди."""
    if not event_id:
        if context.args: 
            event_id = context.args[0]
        else: 
            await update.effective_message.reply_text("⚠️ Ошибка: Мероприятие не выбрано. Используйте /events.")
            return

    # Сохраняем текущее мероприятие для Reply-обработчика
    context.user_data["current_card_event_id"] = event_id

    # Получаем кандидатов вместе с профилями (N+1 Fix: один запрос вместо сотни)
    voters = await candidate_service.get_applicants(event_id)
    if not voters:
        await update.effective_message.reply_text("📭 Нет заявок.")
        return

    # Сохраняем в контекст состояние обхода (весь список данных)
    context.user_data[f"cards_{event_id}"] = {"index": 0, "data": voters}
    
    await _render_card(update, context, event_id, 0)

async def _render_card(update: Update, context: ContextTypes.DEFAULT_TYPE, event_id: str, index: int):
    state = context.user_data.get(f"cards_{event_id}")
    if not state or index >= len(state["data"]):
        await update.effective_message.reply_html(
            "🏁 <b>Все кандидаты просмотрены!</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Вы закончили обзор заявок на это мероприятие. Теперь вы можете перейти к рассылке уведомлений."
        )
        return

    # Получаем данные из кеша (N+1 Optimization)
    v_data = state["data"][index]
    uid = v_data["user_id"]
    cand_profile = v_data.get("candidates", {})
    
    fullname = (cand_profile.get("full_name") or cand_profile.get("first_name")) or "Неизвестно"
    gender_raw = cand_profile.get("gender")
    gender_icon = "👨" if gender_raw == "Male" else "👩" if gender_raw == "Female" else "🧑"
    
    username = cand_profile.get("telegram_username")
    if username:
        username_str = f"@{username.lstrip('@')}"
    else:
        username_str = "Скрыт"
    
    text = (
        f"🙋‍♂️ <b>Карточка кандидата</b>\n"
        f"📦 {index + 1} из {len(state['data'])}\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 <b>ФИО:</b> {fullname}\n"
        f"🔗 <b>Профиль:</b> {username_str}\n"
        f"{gender_icon} <b>Пол:</b> {'Мужской' if gender_raw == 'Male' else 'Женский' if gender_raw == 'Female' else 'Не указан'}\n"
        f"🎭 <b>Роль:</b> {cand_profile.get('primary_role') or 'Не указана'}\n"
        f"⏰ <b>Удобное время:</b> {v_data.get('arrival_time') or 'Не указано'}\n"
        f"📱 <b>Телефон:</b> <code>{cand_profile.get('phone_number') or 'Не указан'}</code>\n\n"
        "✨ <i>Примите решение по кандидату:</i>"
    )
    
    markup = get_candidate_card_keyboard() # Теперь без аргументов, так как Reply
    if update.callback_query:
        await update.callback_query.delete_message()
        await update.effective_chat.send_message(text, reply_markup=markup, parse_mode="HTML")
    else:
        await update.effective_message.reply_html(text, reply_markup=markup)


async def handle_card_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик действий с карточками (Reply-кнопки)."""
    text = update.message.text

    # Кнопка возврата в главное меню — очищаем всё
    if text == "⬅️ В главное меню":
        from utils.keyboards import clear_flow_state
        clear_flow_state(context)
        from telegram import ReplyKeyboardRemove
        await update.message.reply_text("⬅️ Возвращаюсь в главное меню.", reply_markup=ReplyKeyboardRemove())
        from handlers.event_handler import events_dashboard
        await events_dashboard(update, context)
        return

    # Нам нужно найти для какого мероприятия мы сейчас смотрим карточки
    # Мы можем хранить current_card_event_id в user_data
    event_id = context.user_data.get("current_card_event_id")
    if not event_id:
        await update.message.reply_text("⚠️ Сессия истекла. Вернитесь к списку через /events.")
        return

    state = context.user_data.get(f"cards_{event_id}")
    if not state or state["index"] >= len(state.get("data", [])):
        from handlers.event_handler import show_event_management_menu
        await show_event_management_menu(update, context, event_id)
        return

    uid = state["data"][state["index"]]["user_id"]

    if "✅ Принять" in text:
        try:
            await candidate_service.transition_application(event_id, uid, ApplicationStatus.ACCEPTED)
            await update.message.reply_text("✅ Кандидат принят.")
        except Exception as e:
            logger.warning(f"Transition to ACCEPTED failed: {e}")

        state["index"] += 1
        await _render_card(update, context, event_id, state["index"])

    elif "❌ Отклонить" in text:
        try:
            await candidate_service.transition_application(event_id, uid, ApplicationStatus.REJECTED)
            await update.message.reply_text("❌ Кандидат отклонён.")
        except Exception as e:
            logger.warning(f"Transition to REJECTED failed: {e}")

        state["index"] += 1
        await _render_card(update, context, event_id, state["index"])
    elif text == "➡️ Следующий":
        state["index"] += 1
        await _render_card(update, context, event_id, state["index"])
    elif text == "⬅️ Назад к управлению":
        from telegram import ReplyKeyboardRemove
        from handlers.event_handler import show_event_management_menu
        # Убираем клавиатуру карточек перед возвратом
        await update.message.reply_text("⬅️ Возвращаюсь к управлению мероприятием.", reply_markup=ReplyKeyboardRemove())
        await show_event_management_menu(update, context, event_id)

async def handle_card_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split(":")
    action = parts[0]
    event_id = parts[1]
    
    state = context.user_data.get(f"cards_{event_id}")
    if not state: return
    
    current_index = state.get("index", 0)
    if current_index >= len(state.get("data", [])): return

    if action == "card_accept":
        try:
            uid = int(parts[2])
        except (ValueError, IndexError):
            await query.answer("Ошибка данных: ID не число")
            return
        await candidate_service.select_candidate(event_id, uid, True)
        state["index"] += 1
        await _render_card(update, context, event_id, state["index"])
        
    elif action == "card_reject":
        try:
            uid = int(parts[2])
        except (ValueError, IndexError):
            await query.answer("Ошибка данных: ID не число")
            return
        await candidate_service.select_candidate(event_id, uid, False)
        state["index"] += 1
        await _render_card(update, context, event_id, state["index"])
        
    elif action == "card_next":
        state["index"] += 1
        await _render_card(update, context, event_id, state["index"])

# ─── Автоотбор (Этап 6) ──────────────────────────────────────────────────────

async def auto_select_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Функция автоотбора."""
    query = update.callback_query
    if query:
        await query.answer()
        event_id = query.data.split(":")[1]
    else:
        event_id = context.user_data.get("selected_event_id")

    if not event_id:
        return

    event = await event_service.get_event(event_id)
    msg = query.message if query else update.effective_message

    await msg.reply_text(
        f"Сколько кандидатов выбрать для <b>{event.title}</b>?\n\n"
        f"Введите число (нужно сотрудников: {event.max_candidates})",
        parse_mode="HTML"
    )
    context.user_data["auto_select_event"] = event_id
    return # Мы поймаем число в MessageHandler

async def handle_auto_select_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода числа для автоотбора."""
    if not context.user_data:
        return
    event_id = context.user_data.get("auto_select_event")
    if not event_id:
        return
    
    try:
        count = int(update.message.text.strip())
    except:
        await update.message.reply_text("Введите число!")
        return

    voters = await candidate_service.get_applicants(event_id)
    # Берем первых 'count' кандидатов, которые еще не отклонены
    selected_count = 0
    for v in voters:
        if selected_count >= count: break
        await candidate_service.transition_application(event_id, v["user_id"], ApplicationStatus.ACCEPTED)
        selected_count += 1
    
    context.user_data.pop("auto_select_event")
    await update.message.reply_text(
        f"✅ {selected_count} кандидатов выбрано!\n\n"
        "Нажмите /events, чтобы отправить приглашения.",
        reply_markup=get_invitation_keyboard(event_id) # На самом деле лучше через Dashboard
    )


async def set_times_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /set_times <event_id>
    Показывает выбранных кандидатов и просит указать времена.
    Формат: /set_times <event_id> <user_id> <HH:MM> <HH:MM>
    """
    if not await is_recruiter(update.effective_user.id):
        await update.effective_message.reply_text("⛔ У вас нет прав для этой команды.")
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
    selected = await candidate_service.get_applicants(event_id, status=ApplicationStatus.ACCEPTED)
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
    if not context.user_data:
        return
    state = context.user_data.get("st_state")
    if not state:
        return  # Не в состоянии ожидания времени - игнорируем
    
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
        selected = await candidate_service.get_applicants(event_id, status=ApplicationStatus.ACCEPTED)
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
        await update.effective_message.reply_text("⛔ У вас нет прав для этой команды.")
        return
    if not context.args:
        await update.effective_message.reply_text("Использование: /notify_candidates <event_id>")
        return

    event_id = context.args[0]
    event = await event_service.get_event(event_id)
    if not event:
        await update.effective_message.reply_text("❌ Мероприятие не найдено.")
        return

    selected = await candidate_service.get_applicants(event_id, status=ApplicationStatus.ACCEPTED)
    if not selected:
        await update.effective_message.reply_text("❌ Нет одобренных кандидатов для уведомления.")
        return

    sent, failed = 0, 0
    for c in selected:
        user_id = c.get("user_id")
        arrival = c.get("arrival_time", "уточняется")
        departure = c.get("departure_time", "уточняется")
        time_str = f"{arrival} - {departure}" if arrival != "уточняется" and departure != "уточняется" else arrival
        payment_str = event.payment if event.payment else "По договоренности"

        msg = (
            f"🎉 <b>Вы приглашены на мероприятие</b>\n\n"
            f"<b>{event.title}</b>\n\n"
            f"📅 Дата: {event.date}\n"
            f"⏰ Время работы: {time_str}\n"
            f"📍 Место: {event.location}\n"
            f"💰 Оплата: {payment_str}\n\n"
        )
        try:
            await context.bot.send_message(
                chat_id=user_id, text=msg, parse_mode="HTML",
                reply_markup=get_invitation_keyboard(event_id),
            )
            # Переводим в статус INVITED (Шаг 5)
            await candidate_service.transition_application(event_id, user_id, ApplicationStatus.INVITED)
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
    """Callback: кандидат подтверждает/отклоняет участие (Этап 10)."""
    query = update.callback_query
    await query.answer()
    data = query.data
    action, event_id = data.split(":")
    user = query.from_user

    if action == "inv_yes":
        await candidate_service.transition_application(event_id, user.id, ApplicationStatus.CONFIRMED)
        await query.edit_message_text(
            "<b>Отлично!</b>\n\nВы записаны на мероприятие.\n\n"
            "Мы напомним вам за день до начала.",
            parse_mode="HTML",
        )
        # Также отправляем кнопку Check-in (для этапа 11-12)
        await query.message.reply_text(
            "В день мероприятия не забудьте нажать 'Я пришел' в этом чате.",
            reply_markup=get_checkin_keyboard(event_id)
        )
        await audit_service.log_action(event_id, "Candidate Confirmed Participation", user.id)
    else:
        await candidate_service.transition_application(event_id, user.id, ApplicationStatus.DECLINED)
        await query.edit_message_text(
            f"❌ Вы отказались от участия. Спасибо за ответ, {user.first_name}."
        )
        await audit_service.log_action(event_id, "Candidate Declined", user.id)

# ─── Check-in (Этап 12) ──────────────────────────────────────────────────────

async def handle_checkin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Кандидат нажал 'Я пришел'."""
    query = update.callback_query
    await query.answer()
    _, event_id = query.data.split(":")
    user_id = update.effective_user.id
    
    await candidate_service.transition_application(event_id, user_id, ApplicationStatus.CHECKED_IN)
    await query.edit_message_text("✅ Вы отметили свой приход! Рекрутер подтвердит ваше присутствие.")
    
    # Уведомляем рекрутера
    event = await event_service.get_event(event_id)
    if event and event.created_by:
        try:
            cand = await candidate_service.get_candidate_profile(user_id)
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            # Shorten data to avoid 64-byte limit: c_chk:<uuid>:<uid>
            reply_markup = InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ Подтвердить приход", callback_data=f"c_chk:{event_id}:{user_id}")
            ]])
            await context.bot.send_message(
                chat_id=event.created_by,
                text=f"📍 Кандидат <b>{cand.full_name or cand.first_name}</b> пришел на мероприятие <b>{event.title}</b>!",
                parse_mode="HTML",
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.warning(f"BUG-08 [handle_checkin]: Не удалось отправить уведомление рекрутеру: {e}")


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

    await candidate_service.update_candidate_gender(user.id, gender)
    
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
            f"✅ <b>Спасибо!</b> Ваш номер телефона (<code>{phone}</code>) сохранён.\n\n"
            "Пожалуйста, введите ваше <b>ФИО</b> (как в паспорте), чтобы завершить регистрацию:",
            reply_markup=ReplyKeyboardRemove()
        )
        context.user_data["waiting_for_name"] = True
    else:
        await update.effective_message.reply_text("Пожалуйста, отправьте именно свой контакт, используя кнопку в меню.")


async def handle_general_name_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Захват ФИО вне онбординга (общая регистрация)."""
    if not context.user_data:
        return
    if not context.user_data.get("waiting_for_name"):
        return
    
    name = update.message.text.strip()
    user_id = update.effective_user.id
    
    await candidate_service.update_candidate_full_name(user_id, name)
    context.user_data.pop("waiting_for_name")
    
    await update.message.reply_html(
        f"✅ <b>Регистрация завершена!</b>\n\n"
        f"Спасибо, <b>{name}</b>. "
        "Теперь вы будете получать уведомления о новых мероприятиях."
    )

async def handle_confirm_checkin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка нажатия кнопки 'Подтвердить приход' рекрутером."""
    query = update.callback_query
    await query.answer()
    
    # Рекурсивно: c_chk:event_id:user_id
    parts = query.data.split(":")
    if len(parts) < 3:
        return
    
    event_id = parts[1]
    candidate_id = int(parts[2])
    
    # Помечаем что приход подтвержден
    await candidate_service.confirm_checkin(event_id, candidate_id)
    await audit_service.log_action(event_id, "Recruiter Confirmed Check-in", update.effective_user.id, {"candidate_id": candidate_id})
    
    # Обновляем текст сообщения у рекрутера
    cand = await candidate_service.get_candidate_profile(candidate_id)
    await query.edit_message_text(
        text=f"✅ Приход кандидата <b>{cand.full_name or cand.first_name}</b> подтвержден!",
        parse_mode="HTML"
    )
    
    # Опционально: можно отправить сообщение кандидату
    try:
        await context.bot.send_message(
            chat_id=candidate_id,
            text="✅ Рекрутер подтвердил ваш приход на мероприятие! Хорошей смены."
        )
    except:
        pass
