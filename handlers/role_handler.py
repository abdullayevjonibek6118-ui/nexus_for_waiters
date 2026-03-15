"""
Nexus AI — Role Handler
Обработка выбора роли (Рекрутер / Кандидат)
"""
from telegram import Update
from telegram.ext import ContextTypes
from services import recruiter_service, candidate_service
from utils.keyboards import get_gender_inline_keyboard

async def handle_role_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка выбора роли через Reply-кнопки."""
    text = update.message.text
    user = update.effective_user

    if "Рекрутер" in text:
        msg = (
            "👨‍💼 <b>Регистрация рекрутера</b>\n\n"
            "Доступ для рекрутеров предоставляется по подписке.\n"
            "Пожалуйста, свяжитесь с владельцем платформы, чтобы зарегистрировать вашу компанию.\n\n"
            f"Ваш Telegram ID: <code>{user.id}</code> (сообщите его владельцу)."
        )
        await update.message.reply_html(msg)
    
    elif "Кандидат" in text:
        # Начинаем стандартную регистрацию кандидата (выбор пола)
        await candidate_service.get_or_create_candidate(user.id, user.first_name, user.last_name, user.username)
        
        msg = (
            "🙋‍♂️ <b>Регистрация кандидата</b>\n\n"
            "Пожалуйста, <b>выберите ваш пол</b> для завершения регистрации:"
        )
        await update.message.reply_html(msg, reply_markup=get_gender_inline_keyboard())


async def handle_role_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка выбора роли (Inline-версия для обратной совместимости)."""
    query = update.callback_query
    await query.answer()
    
    role = query.data.split(":")[1]
    user = update.effective_user

    if role == "recruiter":
        text = (
            "👨‍💼 <b>Регистрация рекрутера</b>\n\n"
            "Доступ для рекрутеров предоставляется по подписке.\n"
            "Пожалуйста, свяжитесь с владельцем платформы, чтобы зарегистрировать вашу компанию.\n\n"
            f"Ваш Telegram ID: <code>{user.id}</code> (сообщите его владельцу)."
        )
        await query.edit_message_text(text, parse_mode="HTML")
    
    elif role == "candidate":
        await candidate_service.get_or_create_candidate(user.id, user.first_name, user.last_name, user.username)
        
        text = (
            "🙋‍♂️ <b>Регистрация кандидата</b>\n\n"
            "Пожалуйста, <b>выберите ваш пол</b> для завершения регистрации:"
        )
        await query.message.reply_html(text, reply_markup=get_gender_inline_keyboard())
