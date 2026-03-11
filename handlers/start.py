"""
Nexus AI — Handler: /start, /help
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes
from config import settings
from services import recruiter_service, company_service, candidate_service
from utils.keyboards import get_role_selection_keyboard, get_gender_keyboard

logger = logging.getLogger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/start — Приветствие и выбор роли."""
    user = update.effective_user
    
    # 1. Сначала проверяем, не Владелец ли это
    if user.id == settings.super_admin_id:
        await update.message.reply_html(
            f"👑 <b>Здравствуйте, Владелец!</b>\n\n"
            "Вы в режиме супер-админа. Используйте /owner для управления платформой.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⚙️ Панель управления", callback_data="sa:main")]])
        )
        return

    # 2. Проверяем, является ли он рекрутером
    recruiter = await recruiter_service.get_recruiter(user.id)
    if recruiter and recruiter.get("is_active"):
        company = recruiter.get("companies", {})
        # Проверка подписки
        if await company_service.check_subscription(company["id"]):
            await update.message.reply_html(
                f"👋 <b>Приветствуем, {user.first_name}!</b>\n\n"
                f"Вы зарегистрированы как рекрутер компании <b>{company['name']}</b>.\n"
                "Ваши команды управления доступны в /help.",
            )
            return
        else:
            await update.message.reply_html(
                f"⚠️ <b>Внимание!</b>\n\nПодписка вашей компании (<b>{company['name']}</b>) истекла.\n"
                "Свяжитесь с владельцем платформы для продления."
            )
            return

    # 3. Проверяем, является ли он кандидатом
    candidate = await candidate_service.get_candidate_profile(user.id)
    if candidate:
        if candidate.get("gender"):
            text = (
                f"👋 <b>С возвращением, {user.first_name}!</b>\n\n"
                "Вы зарегистрированы как кандидат. Ожидайте новых опросов в группах.\n\n"
                "Если хотите обновить контактные данные — просто отправьте свой номер телефона."
            )
            keyboard = [[KeyboardButton("📞 Поделиться контактом", request_contact=True)]]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
            await update.message.reply_html(text, reply_markup=reply_markup)
            return
        else:
            # Если начал регистрацию, но не закончил выбор пола
            await update.message.reply_html(
                "Пожалуйста, <b>выберите ваш пол</b> для завершения регистрации:",
                reply_markup=get_gender_keyboard()
            )
            return

    # 4. Если абсолютно новый пользователь — предлагаем выбор
    text = (
        "👋 <b>Добро пожаловать в Nexus AI!</b>\n\n"
        "Этот бот помогает рекрутерам управлять персоналом, а кандидатам находить работу.\n\n"
        "<b>Кто вы?</b>"
    )
    await update.message.reply_html(text, reply_markup=get_role_selection_keyboard())


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/help — Справочная информация."""
    user = update.effective_user
    
    # Владелец
    if user.id == settings.super_admin_id:
        text = (
            "👑 <b>Справка владельца:</b>\n\n"
            "/owner — Панель управления компаниями\n"
            "/list_events — Все мероприятия (просмотр)\n"
        )
        await update.message.reply_html(text)
        return

    # Рекрутер
    if await recruiter_service.is_recruiter(user.id):
        text = (
            "👨‍💼 <b>Команды рекрутера:</b>\n\n"
            "/create_event — Создать мероприятие\n"
            "/list_events — Управление мероприятиями\n"
            "/announce <event_id> <текст> — Рассылка\n"
            "/export_excel <event_id> — Выгрузка в Excel\n"
        )
        await update.message.reply_html(text)
        return

    # Кандидат
    text = (
        "🙋‍♂️ <b>Справка кандидата:</b>\n\n"
        "Просто отвечайте на опросы в рабочих группах.\n"
        "Если вам придет приглашение — подтвердите его кнопкой.\n"
        "Чтобы изменить данные — просто напишите боту свой номер или отправьте контакт."
    )
    await update.message.reply_html(text)
