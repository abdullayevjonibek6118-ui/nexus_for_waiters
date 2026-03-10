"""
Nexus AI — Handler: /start, /help
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes
from config import settings

logger = logging.getLogger(__name__)

HELP_ADMIN = """
🤖 <b>Nexus AI Bot — Команды рекрутера</b>

<b>Мероприятия:</b>
/create_event — Создать новое мероприятие
/list_events — Список активных мероприятий

<b>Опрос:</b>
/publish_poll &lt;event_id&gt; — Опубликовать опрос в группу
/close_poll &lt;event_id&gt; — Закрыть опрос

<b>Кандидаты:</b>
/voters &lt;event_id&gt; — Кто проголосовал
/select_candidates &lt;event_id&gt; — Отметить выбранных
/set_times &lt;event_id&gt; — Назначить время прихода/ухода
/notify_candidates &lt;event_id&gt; — Уведомить выбранных
/announce &lt;event_id&gt; &lt;text&gt; — Разослать сообщение выбранным

<b>Таблица и учёт:</b>
/create_sheet &lt;event_id&gt; — Создать Google Sheet
/payment_reminder &lt;event_id&gt; — Запланировать напоминание об оплате
/payment_confirmed &lt;event_id&gt; — Отменить напоминание (оплата получена)

<b>Аудит:</b>
/logs &lt;event_id&gt; — Посмотреть лог мероприятия
"""

HELP_CANDIDATE = """
🤖 <b>Nexus AI Bot</b>

Привет! Этот бот управляет приглашениями на мероприятия.

Если вас выберут на мероприятие, вы получите личное сообщение с деталями.
Вам нужно будет подтвердить или отклонить участие.

📞 Поделитесь своим контактом кнопкой ниже, чтобы рекрутер мог связаться с вами.
"""


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start."""
    user = update.effective_user
    is_admin = user.id in settings.admin_ids

    if is_admin:
        text = (
            f"👋 Добро пожаловать, <b>{user.first_name}</b>!\n\n"
            f"Вы вошли как <b>рекрутер</b>.\n"
            f"Используйте /help для списка команд."
        )
        await update.message.reply_html(text)
    else:
        # Проверяем профиль кандидата
        candidate = await candidate_service.get_candidate_profile(user.id)
        
        if not candidate or not candidate.gender:
            text = (
                f"👋 Привет, <b>{user.first_name}</b>!\n\n"
                f"Это Nexus AI бот для управления мероприятиями.\n"
                f"Пожалуйста, <b>выберите ваш пол</b> для завершения регистрации:"
            )
            from utils.keyboards import get_gender_keyboard
            await update.message.reply_html(text, reply_markup=get_gender_keyboard())
            return

        text = (
            f"👋 Привет, <b>{user.first_name}</b>!\n\n"
            f"Это Nexus AI бот для управления мероприятиями.\n"
            f"Используйте /help для информации.\n"
            f"Пожалуйста, поделитесь своим контактом, чтобы мы могли связаться с вами."
        )
        from telegram import ReplyKeyboardMarkup, KeyboardButton
        keyboard = [[KeyboardButton("📞 Поделиться контактом", request_contact=True)]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        await update.message.reply_html(text, reply_markup=reply_markup)
    logger.info(f"Пользователь {user.id} ({user.first_name}) запустил бота")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /help."""
    user = update.effective_user
    is_admin = user.id in settings.admin_ids
    text = HELP_ADMIN if is_admin else HELP_CANDIDATE
    await update.message.reply_html(text)
