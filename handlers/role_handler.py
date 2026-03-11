"""
Nexus AI — Role Handler
Обработка выбора роли (Рекрутер / Кандидат)
"""
from telegram import Update
from telegram.ext import ContextTypes
from services import recruiter_service, candidate_service
from utils.keyboards import get_gender_keyboard

async def handle_role_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка выбора роли."""
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
        # Начинаем стандартную регистрацию кандидата (выбор пола)
        # Сначала создаем запись в кандидатах, чтобы он был в базе
        await candidate_service.get_or_create_candidate(user.id, user.first_name, user.last_name, user.username)
        
        text = (
            "🙋‍♂️ <b>Регистрация кандидата</b>\n\n"
            "Пожалуйста, <b>выберите ваш пол</b> для завершения регистрации:"
        )
        await query.edit_message_text(text, reply_markup=get_gender_keyboard(), parse_mode="HTML")
