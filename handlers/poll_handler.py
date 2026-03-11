"""
Nexus AI — Handler: Опросы
Команды: /publish_poll, /close_poll + PollAnswerHandler
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes
from config import settings
from models.candidate import VoteStatus
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

        text = (
            "📢 <b>Работа на мероприятии</b>\n\n"
            f"<b>{event.title}</b>\n\n"
            f"📅 Дата: {event.date}\n"
            f"📍 Место: {event.location}\n"
            f"💰 Оплата: {event.payment or 'По договоренности'}\n\n"
            f"Нужны сотрудники:\n{roles_text}\n\n"
            "👇 Чтобы участвовать нажмите кнопку"
        )

        # Получаем компанию рекрутера для Chat ID
        rec_profile = await recruiter_service.get_recruiter(update.effective_user.id)
        group_chat_id = rec_profile["companies"].get("group_chat_id") if rec_profile and rec_profile.get("companies") else settings.group_chat_id

        if not group_chat_id:
            await update.effective_message.reply_text("⚠️ ID группы не настроен.")
            return

        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        bot_username = (await context.bot.get_me()).username
        url = f"https://t.me/{bot_username}?start=event_{event_id}"
        keyboard = [[InlineKeyboardButton("Участвовать", url=url)]]
        
        await context.bot.send_message(
            chat_id=group_chat_id,
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )

        await event_service.save_poll_id(event_id, "hiring_msg") # Помечаем что опубликовано
        await audit_service.log_action(event_id, "Hiring Published", update.effective_user.id)

        await update.effective_message.reply_text("✅ Объявление о наборе опубликовано в группе!")

    except Exception as e:
        logger.error(f"Ошибка публикации: {e}")
        await update.effective_message.reply_text(f"❌ Ошибка: {e}")

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

    from models.event import EventStatus
    await event_service.update_event_status(event_id, EventStatus.SELECTION_COMPLETED)
    await audit_service.log_action(event_id, "poll_closed", update.effective_user.id, {})

    voters = await candidate_service.get_voters(event_id)
    text = (
        f"✅ Опрос закрыт!\n\n"
        f"📊 Проголосовавших: <b>{len(voters)}</b>\n\n"
        f"Используйте /voters {event_id} чтобы увидеть список\n"
        f"или /select_candidates {event_id} чтобы отобрать кандидатов."
    )
    await update.effective_message.reply_html(text)

async def handle_poll_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    PollAnswerHandler — фиксирует каждый ответ на опрос.
    """
    poll_answer = update.poll_answer
    user_id = poll_answer.user.id
    poll_id = str(poll_answer.poll_id)
    option_ids = poll_answer.option_ids

    # Найти мероприятие по poll_id
    event = await event_service.get_event_by_poll_id(poll_id)
    if not event:
        logger.warning(f"PollAnswer: мероприятие не найдено для poll_id={poll_id}")
        return

    # Определить статус голоса
    if not option_ids:
        # Пользователь отозвал голос
        vote = VoteStatus.NO
    elif option_ids[0] == 0:
        vote = VoteStatus.YES
    elif option_ids[0] == 1:
        vote = VoteStatus.MAYBE
    else:
        vote = VoteStatus.NO

    # Создать профиль кандидата если нет
    user = poll_answer.user
    await candidate_service.get_or_create_candidate(
        user_id=user.id,
        first_name=user.first_name or "—",
        last_name=user.last_name,
        username=user.username,
    )

    # Сохранить голос
    await candidate_service.save_vote(event.event_id, user_id, vote)
    logger.info(f"Голос сохранён: user={user_id}, event={event.event_id}, vote={vote}")
