"""
Nexus AI — Handler: Опросы
Команды: /publish_poll, /close_poll + PollAnswerHandler
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes
from config import settings
from models.candidate import VoteStatus
from services import event_service, candidate_service, audit_service

logger = logging.getLogger(__name__)


def is_admin(user_id: int) -> bool:
    return user_id in settings.admin_ids


async def publish_poll(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /publish_poll <event_id>
    Публикует опрос в групповой чат.
    """
    if not is_admin(update.effective_user.id):
        await update.effective_message.reply_text("⛔ У вас нет прав для этой команды.")
        return

    if not context.args:
        await update.effective_message.reply_text("Использование: /publish_poll <event_id>")
        return

    event_id = context.args[0]
    event = await event_service.get_event(event_id)
    if not event:
        await update.effective_message.reply_text(f"❌ Мероприятие {event_id} не найдено.")
        return

    # Публикуем опрос в группу
    req_text = ""
    if event.required_men > 0 or event.required_women > 0:
        req_text = f"\n👥 Нужно: М {event.required_men}, Ж {event.required_women}"

    question = f"📅 {event.title} | {event.date} в {event.location}{req_text}"
    options = [
        "✅ Приду (Да)",
        "🤔 Возможно",
        "❌ Не приду",
    ]

    try:
        group_chat_id = settings.group_chat_id
        if group_chat_id == 0:
            await update.effective_message.reply_text(
                "⚠️ GROUP_CHAT_ID не задан в .env! Укажи ID группового чата."
            )
            return

        poll_msg = await context.bot.send_poll(
            chat_id=group_chat_id,
            question=question,
            options=options,
            is_anonymous=False,        # не анонимный — видно кто проголосовал
            allows_multiple_answers=False,
        )

        poll_id = str(poll_msg.poll.id)
        await event_service.save_poll_id(event_id, poll_id)
        await audit_service.log_action(event_id, "poll_published", update.effective_user.id,
                                        {"poll_id": poll_id})

        await update.effective_message.reply_html(
            f"✅ Опрос опубликован!\n\n"
            f"🆔 Poll ID: <code>{poll_id}</code>\n"
            f"📊 Статус мероприятия: Poll_Published\n\n"
            f"Используйте /close_poll {event_id} чтобы закрыть опрос."
        )

    except Exception as e:
        logger.error(f"Ошибка публикации опроса: {e}")
        await update.effective_message.reply_text(f"❌ Ошибка публикации опроса: {e}")


async def close_poll(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /close_poll <event_id>
    Закрывает опрос и переводит мероприятие в Selection_Completed.
    """
    if not is_admin(update.effective_user.id):
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
