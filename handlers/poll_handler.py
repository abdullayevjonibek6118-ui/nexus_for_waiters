"""
Nexus AI — Handler: Опросы
Команды: /publish_poll, /close_poll + PollAnswerHandler
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import settings
from utils.constants import VoteStatus, EventStatus
from services import event_service, candidate_service, audit_service, recruiter_service

logger = logging.getLogger(__name__)

async def is_recruiter(user_id: int) -> bool:
    """Проверка прав: Владелец или Рекрутер."""
    if user_id == settings.super_admin_id:
        return True
    return await recruiter_service.is_recruiter(user_id)

async def publish_poll(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Публикует сообщение о наборе (Этап 4 в сценарии).
    """
    if not await is_recruiter(update.effective_user.id):
        await update.effective_message.reply_text("⛔ У вас нет прав для этой команды.")
        return

    event_id = None
    if context.args:
        event_id = context.args[0]
    elif context.user_data.get("current_event_id"):
        event_id = context.user_data.get("current_event_id")

    if not event_id:
        await update.effective_message.reply_text("Использование: /publish_poll <event_id>")
        return

    event = await event_service.get_event(event_id)
    if not event:
        await update.effective_message.reply_text(f"❌ Мероприятие не найдено.")
        return

    try:
        # Формируем текст сообщения
        roles_text = "\n".join([f"• {r}" for r in (event.required_roles or [])])
        if not roles_text:
            roles_text = "• Промоутеры\n• Хостес\n• Регистраторы"

        times_text = ", ".join(event.arrival_times) if event.arrival_times else "Не указано"
        text = (
            "📢 <b>Работа на мероприятии</b>\n\n"
            f"<b>{event.title}</b>\n\n"
            f"📅 Дата: {event.date}\n"
            f"⏰ Начало: {times_text}\n"
            f"🏁 Конец: {event.end_time or '—'}\n"
            f"📍 Место: {event.location}\n"
            f"💰 Оплата: {event.payment or 'По договоренности'}\n\n"
            f"Нужны сотрудники:\n{roles_text}\n\n"
            "👇 Чтобы участвовать нажмите кнопку"
        )

        # Получаем компанию рекрутера для Chat ID
        rec_profile = await recruiter_service.get_recruiter(update.effective_user.id)
        group_chat_id = None
        if rec_profile and rec_profile.get("companies"):
            group_chat_id = rec_profile["companies"].get("group_chat_id")
        
        # Если в компании не настроено, берем из конфига
        if not group_chat_id or group_chat_id == 0:
            group_chat_id = settings.group_chat_id

        if not group_chat_id or group_chat_id == 0:
            await update.effective_message.reply_text("⚠️ ID группы не настроен. Пожалуйста, укажите GROUP_CHAT_ID в .env или в настройках компании.")
            return

        bot_username = (await context.bot.get_me()).username
        url = f"https://t.me/{bot_username}?start=event_{event_id}"
        keyboard = [[InlineKeyboardButton("Зарегистрироваться", url=url)]]
        
        sent_message = await context.bot.send_message(
            chat_id=group_chat_id,
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )

        saved_info = await event_service.save_poll_published_info(
            event_id, 
            "hiring_msg", 
            str(group_chat_id), 
            str(sent_message.message_id)
        )
        
        if saved_info:
            await audit_service.log_action(event_id, "Hiring Published", update.effective_user.id)
            await update.effective_message.reply_text("✅ Объявление о наборе опубликовано и ID зафиксированы!")
        else:
            await update.effective_message.reply_text("⚠️ Пост отправлен, но данные в базе НЕ ОБНОВИЛИСЬ. Проверьте структуру таблицы.")

    except Exception as e:
        logger.error(f"Ошибка публикации в чат: {e}")
        await update.effective_message.reply_text(f"❌ Ошибка публикации: {e}")

async def close_poll(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /close_poll <event_id>
    Закрывает опрос и переводит мероприятие в Selection_Completed.
    """
    if not await is_recruiter(update.effective_user.id):
        await update.effective_message.reply_text("⛔ У вас нет прав для этой команды.")
        return

    if not context.args:
        await update.effective_message.reply_text("Использование: /close_poll <event_id>")
        return

    event_id = context.args[0]
    event = await event_service.get_event(event_id)
    if not event or not event.poll_id:
        await update.effective_message.reply_text(f"❌ Мероприятие {event_id} не найдено или опрос не опубликован.")
        return

    await event_service.update_event_status(event_id, EventStatus.SELECTION_COMPLETED)
    await audit_service.log_action(event_id, "poll_closed", update.effective_user.id, {})
    await update.effective_message.reply_text(f"✅ Опрос для мероприятия {event_id} закрыт.")
