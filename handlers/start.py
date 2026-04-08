"""
Nexus AI — Handler: /start, /help
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes
from config import settings
from services import recruiter_service, company_service, candidate_service
from utils.keyboards import get_role_selection_keyboard, get_gender_inline_keyboard

from handlers.onboarding_handler import start_onboarding

logger = logging.getLogger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/start — Приветствие и выбор роли."""
    user = update.effective_user
    args = context.args # Параметры после /start

    # ПРОВЕРКА DEEP LINKING (Этап 1)
    if args and args[0].startswith("event_"):
        event_id = args[0].replace("event_", "")
        user_id = user.id

        # Проверяем, зарегистрирован ли пользователь уже на это мероприятие
        existing_app = await candidate_service.get_event_candidate(event_id, user_id)

        if existing_app:
            status = existing_app.get("application_status", "")
            role = existing_app.get("role", "")
            arrival = existing_app.get("arrival_time", "")

            # Терминальные статусы — нельзя перерегистрироваться
            terminal_statuses = {"REJECTED", "DECLINED", "CHECKED_IN"}
            if status in terminal_statuses:
                status_messages = {
                    "REJECTED": "❌ К сожалению, ваша заявка была отклонена.",
                    "DECLINED": "⚠️ Вы ранее отказались от участия в этом мероприятии.",
                    "CHECKED_IN": "✅ Вы уже отметились на этом мероприятии. Хорошей смены!"
                }
                await update.message.reply_text(status_messages.get(status, "Ваш статус: " + status))
                return

            # Нетерминальные статусы — пользователь уже зарегистрирован
            active_messages = {
                "PENDING": "⏳ Ваша заявка на участие уже принята и ожидает рассмотрения.",
                "ACCEPTED": "✅ Вы уже приняты на это мероприятие!",
                "SCHEDULED": "⏰ Вам уже назначено время. Ожидайте приглашения.",
                "INVITED": "📨 Вам уже отправлено приглашение. Проверьте чат с ботом.",
                "CONFIRMED": "✅ Вы уже подтвердили участие. Ждём вас в день мероприятия!"
            }

            role_info = f"\n🎭 Роль: {role}" if role else ""
            time_info = f"\n⏰ Время: {arrival}" if arrival else ""

            await update.message.reply_html(
                f"👋 <b>{user.first_name}</b>, вы уже зарегистрированы на это мероприятие.{role_info}{time_info}\n\n"
                f"{active_messages.get(status, f'Статус: {status}')}\n\n"
                f"Если хотите изменить данные, используйте /start и следуйте инструкциям."
            )
            return

        # Пользователь ещё не регистрировался на это мероприятие — начинаем онбординг
        return await start_onboarding(update, context, event_id)
    
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
        if candidate.gender:
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
                reply_markup=get_gender_inline_keyboard()
            )
            return

    # 4. Если абсолютно новый пользователь — предлагаем выбор
    text = (
        "✨ <b>Добро пожаловать в Nexus AI!</b> ✨\n\n"
        "Мы создаем идеальную среду для взаимодействия между рекрутерами и персоналом.\n\n"
        "🚀 <b>Наши возможности:</b>\n"
        "• Мгновенный поиск персонала на мероприятия\n"
        "• Удобный онбординг и управление сменами\n"
        "• Автоматизация отчетов и логов\n\n"
        "🛡 Пожалуйста, <b>выберите вашу роль</b> для начала работы:"
    )
    await update.message.reply_html(text, reply_markup=get_role_selection_keyboard())


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/help — Справочная информация (Premium UI)."""
    user = update.effective_user
    
    # Владелец
    if user.id == settings.super_admin_id:
        text = (
            "👑 <b>Панель Владельца</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "🔹 /owner — Управление компаниями и подписками\n"
            "🔹 /list_events — Мониторинг всех мероприятий\n"
            "🔹 /logs — Системные логи\n\n"
            "<i>Вы имеете неограниченный доступ ко всем функциям платформы.</i>"
        )
        await update.message.reply_html(text)
        return

    # Рекрутер
    if await recruiter_service.is_recruiter(user.id):
        text = (
            "👨‍💼 <b>Инструменты Рекрутера</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "🔹 /events — <b>Ваш Дашборд</b> (Создание и управление)\n"
            "🔹 /create_event — Быстрый запуск мероприятия\n"
            "🔹 /list_events — Активные проекты\n\n"
            "📢 <b>Рассылки и Экспорт:</b>\n"
            "• <code>/announce [ID] [текст]</code> — Сообщение кандидатам\n"
            "• <code>/export_excel [ID]</code> — Скачать отчет\n\n"
            "💡 <i>Используйте интерактивное меню в /events для удобного управления.</i>"
        )
        await update.message.reply_html(text)
        return

    # Кандидат
    text = (
        "🙋‍♂️ <b>Личный кабинет Кандидата</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "👋 Рады видеть вас в нашей базе персонала!\n\n"
        "📍 <b>Как это работает:</b>\n"
        "1. Следите за опросами в рабочих группах.\n"
        "2. Жмите <b>«Участвовать»</b> и проходите короткую регистрацию.\n"
        "3. В день мероприятия жмите <b>«Я на месте»</b> в боте.\n\n"
        "📱 <b>Личные данные:</b>\n"
        "Чтобы обновить контакт или ФИО, просто отправьте сообщение боту.\n\n"
        "✨ <i>Желаем продуктивной работы!</i>"
    )
    await update.message.reply_html(text)
