"""
Nexus AI — Candidate Onboarding Handler
Сценарий: Регистрация кандидата на мероприятие (Этапы 1-8)
"""
import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, CallbackQueryHandler, filters

from services import candidate_service, event_service, audit_service
from utils.keyboards import (
    get_onboarding_start_keyboard,
    get_dynamic_choice_keyboard,
    get_onboarding_confirm_keyboard,
)

logger = logging.getLogger(__name__)

# Состояния
WAIT_REG_START, CHOOSE_ROLE, SHARE_PHONE, INPUT_NAME, CHOOSE_GENDER, CHOOSE_TIME, CONFIRM_DATA = range(7)

async def start_onboarding(update: Update, context: ContextTypes.DEFAULT_TYPE, event_id: str):
    """Начало онбординга (Этап 2)."""
    context.user_data["ob_event_id"] = event_id
    
    text = (
        "👋 <b>Nexus AI: Регистрация</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "Мы поможем вам быстро подготовить профиль для работы на этом мероприятии.\n\n"
        "⏳ <i>Это займет меньше минуты.</i>"
    )
    await update.message.reply_html(text, reply_markup=get_onboarding_start_keyboard(event_id))
    return WAIT_REG_START

async def handle_ob_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Шаг 1: Роль."""
    query = update.callback_query
    await query.answer()
    
    event_id = context.user_data.get("ob_event_id")
    event = await event_service.get_event(event_id)
    roles = event.required_roles or ["Промоутер", "Хостес", "Регистратор"]
    
    await query.edit_message_text(
        "📝 <b>Шаг 1 из 4: Ваша роль</b>\n\nВыберите позицию, на которой вы хотите работать:",
        reply_markup=get_dynamic_choice_keyboard(roles, "ob_role"),
        parse_mode="HTML"
    )
    return CHOOSE_ROLE

async def handle_role_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Шаг 2: Телефон."""
    query = update.callback_query
    await query.answer()
    
    role = query.data.split(":")[1]
    context.user_data["ob_role"] = role
    
    keyboard = [[KeyboardButton("📞 Поделиться контактом", request_contact=True)]]
    await query.message.reply_text(
        "📱 <b>Шаг 2 из 4: Контактные данные</b>\n\nНажмите кнопку ниже, чтобы отправить номер телефона:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True),
        parse_mode="HTML"
    )
    return SHARE_PHONE

async def handle_phone_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Шаг 3: ФИО."""
    contact = update.message.contact
    phone = contact.phone_number
    context.user_data["ob_phone"] = phone
    
    await update.message.reply_html(
        "👤 <b>Шаг 3 из 4: Ваше имя</b>\n\nВведите ваше <b>ФИО</b> полностью (как в паспорте):",
        reply_markup=ReplyKeyboardRemove()
    )
    return INPUT_NAME

async def handle_name_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Шаг 4: Пол."""
    name = update.message.text.strip()
    context.user_data["ob_full_name"] = name
    
    from telegram import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = [[
        InlineKeyboardButton("👨 Мужской", callback_data="ob_gender:Male"),
        InlineKeyboardButton("👩 Женский", callback_data="ob_gender:Female")
    ]]
    await update.message.reply_html(
        "🚻 <b>Шаг 4 из 5: Ваш пол</b>\n\nПожалуйста, выберите ваш пол:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return CHOOSE_GENDER

async def handle_gender_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Шаг 5: Время."""
    query = update.callback_query
    await query.answer()
    
    gender = query.data.split(":")[1]
    context.user_data["ob_gender"] = gender
    
    event_id = context.user_data.get("ob_event_id")
    event = await event_service.get_event(event_id)
    times = event.arrival_times or ["08:00", "09:00", "10:00"]
    
    await query.edit_message_text(
        f"⏰ <b>Шаг 5 из 5: Время прихода</b>\n\nВыберите удобное время начала смены:",
        reply_markup=get_dynamic_choice_keyboard(times, "ob_time"),
        parse_mode="HTML"
    )
    return CHOOSE_TIME

async def handle_time_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор времени (Этап 7)."""
    query = update.callback_query
    await query.answer()
    
    time = query.data.split(":")[1]
    context.user_data["ob_time"] = time
    
    full_name = context.user_data.get("ob_full_name")
    role = context.user_data.get("ob_role")
    phone = context.user_data.get("ob_phone")
    
    text = (
        "🏁 <b>Почти готово! Проверьте данные:</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 <b>ФИО:</b> {full_name}\n"
        f"🎭 <b>Роль:</b> {role}\n"
        f"📱 <b>Тел:</b> {phone}\n"
        f"⏰ <b>Время:</b> {time}\n\n"
        "<i>Если всё верно, нажмите «Подтвердить».</i>"
    )
    
    event_id = context.user_data.get("ob_event_id")
    await query.edit_message_text(
        text, 
        reply_markup=get_onboarding_confirm_keyboard(event_id),
        parse_mode="HTML"
    )
    return CONFIRM_DATA

async def handle_ob_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение (Этап 8)."""
    query = update.callback_query
    await query.answer()
    
    event_id = context.user_data.get("ob_event_id")
    user = update.effective_user
    user_id = user.id
    full_name = context.user_data.get("ob_full_name")
    role = context.user_data.get("ob_role")
    phone = context.user_data.get("ob_phone")
    gender = context.user_data.get("ob_gender")
    
    # BUG-05: Создаём профиль перед регистрацией (Foreign Key Guard)
    await candidate_service.get_or_create_candidate(user_id, user.first_name, user.last_name, user.username)
    
    # Сохраняем данные
    await candidate_service.update_candidate_full_name(user_id, full_name)
    await candidate_service.update_phone_number(user_id, phone)
    await candidate_service.update_candidate_gender(user_id, gender) # Сохраняем пол
    await candidate_service.update_candidate_role(user_id, role)  # BUG-06: явно сохраняем роль
    await candidate_service.register_for_event(event_id, user_id, role, context.user_data.get("ob_time"))
    
    # BUG-07: Премиум сообщение подтверждения
    await query.edit_message_text(
        "🎉 <b>Заявка отправлена!</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "Рекрутер просмотрит вашей заявку и свяжется с вами если выберет вас.\n\n"
        "⏳ <i>Ожидайте уведомления. Удачи!</i>",
        parse_mode="HTML"
    )
    
    await audit_service.log_action(event_id, "Candidate Registered", user_id, {
        "full_name": full_name,
        "role": role,
        "time": context.user_data.get("ob_time")
    })
    
    return ConversationHandler.END

async def handle_ob_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Возврат к началу регистрации (к выбору роли)."""
    query = update.callback_query
    await query.answer()
    
    # UI-02: Очищаем устаревшие данные в user_data
    for key in ["ob_role", "ob_phone", "ob_full_name", "ob_time"]:
        context.user_data.pop(key, None)
    
    event_id = context.user_data.get("ob_event_id")
    event = await event_service.get_event(event_id)
    roles = event.required_roles or ["Промоутер", "Хостес", "Регистратор"]
    
    await query.edit_message_text(
        "📝 <b>Шаг 1 из 4: Ваша роль</b>\n\nВыберите позицию:",
        reply_markup=get_dynamic_choice_keyboard(roles, "ob_role"),
        parse_mode="HTML"
    )
    return CHOOSE_ROLE

def get_onboarding_handler():
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(handle_ob_start, pattern="^ob_start:")
        ],
        states={
            WAIT_REG_START: [CallbackQueryHandler(handle_ob_start, pattern=r"^ob_start:")],
            CHOOSE_ROLE: [CallbackQueryHandler(handle_role_choice, pattern=r"^ob_role:")],
            SHARE_PHONE: [MessageHandler(filters.CONTACT, handle_phone_input)],
            INPUT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_name_input)],
            CHOOSE_GENDER: [CallbackQueryHandler(handle_gender_choice, pattern=r"^ob_gender:")],
            CHOOSE_TIME: [CallbackQueryHandler(handle_time_choice, pattern=r"^ob_time:")],
            CONFIRM_DATA: [
                CallbackQueryHandler(handle_ob_confirm, pattern=r"^ob_confirm:"),
                CallbackQueryHandler(handle_ob_edit, pattern=r"^ob_edit:")
            ]
        },
        fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)],
        allow_reentry=True,
        name="candidate_onboarding",
        persistent=False
    )
