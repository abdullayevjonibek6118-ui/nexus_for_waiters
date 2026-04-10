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
    user = update.effective_user
    user_id = user.id

    # Проверяем, есть ли у пользователя уже заполненный профиль
    existing_profile = await candidate_service.get_candidate_profile(user_id)

    # Всегда показываем inline-кнопку "Начать регистрацию" — это entry point ConversationHandler
    # Без этого ConversationHandler не активируется и следующие сообщения не обрабатываются
    text = (
        "👋 <b>Nexus AI: Регистрация</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
    )
    if existing_profile and existing_profile.gender and existing_profile.phone_number:
        text += "Ваш профиль уже сохранён. Осталось только выбрать роль для этого мероприятия."
    else:
        text += "Мы поможем вам быстро подготовить профиль для работы на этом мероприятии.\n\n"
        text += "⏳ <i>Это займет меньше минуты.</i>"

    await update.message.reply_html(
        text,
        reply_markup=get_onboarding_start_keyboard(event_id)
    )
    return WAIT_REG_START

async def handle_ob_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Шаг 1: Роль."""
    if update.callback_query:
        await update.callback_query.answer()
        message = update.callback_query.message
    else:
        message = update.message

    user_id = update.effective_user.id

    # Определяем, есть ли у пользователя уже заполненный профиль
    existing_profile = await candidate_service.get_candidate_profile(user_id)
    has_profile = existing_profile and existing_profile.gender and existing_profile.phone_number

    if has_profile:
        context.user_data["ob_has_profile"] = True
        context.user_data["ob_full_name"] = existing_profile.full_name
        context.user_data["ob_phone"] = existing_profile.phone_number
        context.user_data["ob_gender"] = existing_profile.gender

    event_id = context.user_data.get("ob_event_id")
    event = await event_service.get_event(event_id)
    roles = event.required_roles or ["Промоутер", "Хостес", "Регистратор"]

    from utils.keyboards import get_onboarding_role_reply_keyboard

    if has_profile:
        text = (
            f"👋 <b>С возвращением, {existing_profile.full_name or update.effective_user.first_name}!</b>\n\n"
            "📝 <b>Шаг 1 из 1: Ваша роль</b>\n\n"
            "Выберите позицию, на которой вы хотите работать:"
        )
    else:
        context.user_data["ob_has_profile"] = False
        text = (
            "📝 <b>Шаг 1 из 5: Ваша роль</b>\n\n"
            "Выберите позицию, на которой вы хотите работать:"
        )

    await message.reply_html(
        text,
        reply_markup=get_onboarding_role_reply_keyboard(roles)
    )
    return CHOOSE_ROLE

async def handle_role_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Шаг 2: Телефон (или пропуск если профиль уже есть)."""
    role = update.message.text.strip()
    context.user_data["ob_role"] = role

    has_profile = context.user_data.get("ob_has_profile", False)

    if has_profile:
        # Профиль уже заполнен — пропускаем телефон, имя, пол и сразу переходим к выбору времени
        event_id = context.user_data.get("ob_event_id")
        event = await event_service.get_event(event_id)
        times = event.arrival_times or ["08:00", "09:00", "10:00"]

        from utils.keyboards import get_onboarding_time_reply_keyboard
        await update.message.reply_html(
            "⏰ <b>Шаг 1 из 1: Время прихода</b>\n\nВыберите удобное время начала смены:",
            reply_markup=get_onboarding_time_reply_keyboard(times)
        )
        return CHOOSE_TIME

    # Новый пользователь — запрашиваем контакт
    keyboard = [[KeyboardButton("📞 Поделиться контактом", request_contact=True)]]
    await update.message.reply_html(
        "📱 <b>Шаг 2 из 5: Контактные данные</b>\n\nНажмите кнопку ниже, чтобы отправить номер телефона:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    )
    return SHARE_PHONE

async def handle_phone_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Шаг 3: ФИО."""
    contact = update.message.contact
    phone = contact.phone_number
    context.user_data["ob_phone"] = phone
    
    await update.message.reply_html(
        "👤 <b>Шаг 3 из 5: Ваше имя</b>\n\nВведите ваше <b>ФИО</b> полностью (как в паспорте):",
        reply_markup=ReplyKeyboardRemove()
    )
    return INPUT_NAME

async def handle_name_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Шаг 4: Пол."""
    name = update.message.text.strip()
    context.user_data["ob_full_name"] = name
    
    from utils.keyboards import get_onboarding_gender_reply_keyboard
    await update.message.reply_html(
        "🚻 <b>Шаг 4 из 5: Ваш пол</b>\n\nПожалуйста, выберите ваш пол:",
        reply_markup=get_onboarding_gender_reply_keyboard()
    )
    return CHOOSE_GENDER

async def handle_gender_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Шаг 5: Время."""
    gender_text = update.message.text.strip()
    # Конвертируем обратно в Enum-совместимую строку
    gender = "Male" if "Мужской" in gender_text else "Female"
    context.user_data["ob_gender"] = gender
    
    event_id = context.user_data.get("ob_event_id")
    event = await event_service.get_event(event_id)
    times = event.arrival_times or ["08:00", "09:00", "10:00"]
    
    from utils.keyboards import get_onboarding_time_reply_keyboard
    await update.message.reply_html(
        f"⏰ <b>Шаг 5 из 5: Время прихода</b>\n\nВыберите удобное время начала смены:",
        reply_markup=get_onboarding_time_reply_keyboard(times)
    )
    return CHOOSE_TIME

async def handle_time_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор времени (Этап 7)."""
    time = update.message.text.strip()
    context.user_data["ob_time"] = time
    
    full_name = context.user_data.get("ob_full_name")
    role = context.user_data.get("ob_role")
    phone = context.user_data.get("ob_phone")

    event_id = context.user_data.get("ob_event_id")
    event = await event_service.get_event(event_id)
    end_time_str = f" — {event.end_time}" if event.end_time else ""
    
    text = (
        "🏁 <b>Почти готово! Проверьте данные:</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 <b>ФИО:</b> {full_name}\n"
        f"🎭 <b>Роль:</b> {role}\n"
        f"📱 <b>Тел:</b> {phone}\n"
        f"⏰ <b>Время:</b> {time}{end_time_str}\n\n"
        "<i>Если всё верно, нажмите «Подтвердить».</i>"
    )
    
    from utils.keyboards import get_onboarding_confirm_reply_keyboard
    await update.message.reply_html(
        text, 
        reply_markup=get_onboarding_confirm_reply_keyboard()
    )
    return CONFIRM_DATA

async def handle_ob_confirm_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик финального выбора: Подтвердить или Изменить."""
    action_text = update.message.text.strip()
    
    logger.debug(f"Onboarding confirm action: '{action_text}'")
    
    if action_text == "✅ Подтвердить":
        return await handle_ob_confirm(update, context)
    elif action_text == "✏️ Изменить":
        return await handle_ob_edit(update, context)
    else:
        logger.warning(f"Unknown onboarding action: '{action_text}'")
        return CONFIRM_DATA

async def handle_ob_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение (Этап 8)."""
    logger.info(f"User {update.effective_user.id} confirming onboarding")
    event_id = context.user_data.get("ob_event_id")
    user = update.effective_user
    user_id = user.id
    full_name = context.user_data.get("ob_full_name")
    role = context.user_data.get("ob_role")
    phone = context.user_data.get("ob_phone")
    gender = context.user_data.get("ob_gender")
    has_profile = context.user_data.get("ob_has_profile", False)

    # Создаём/получаем профиль (Foreign Key Guard)
    await candidate_service.get_or_create_candidate(user_id, user.first_name, user.last_name, user.username)

    # Сохраняем личные данные только если профиль не был загружен из существующего
    if not has_profile:
        await candidate_service.update_candidate_full_name(user_id, full_name)
        await candidate_service.update_phone_number(user_id, phone)
        await candidate_service.update_candidate_gender(user_id, gender)

    # Регистрируем на ивент (через новую функцию)
    event = await event_service.get_event(event_id)
    await candidate_service.apply_for_event(
        event_id=event_id,
        user_id=user_id,
        role=role,
        arrival_time=context.user_data.get("ob_time"),
        departure_time=event.end_time
    )

    # Премиум сообщение подтверждения
    await update.message.reply_html(
        "🎉 <b>Заявка отправлена!</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "Рекрутер просмотрит вашей заявку и свяжется с вами если выберет вас.\n\n"
        "⏳ <i>Ожидайте уведомления. Удачи!</i>",
        reply_markup=ReplyKeyboardRemove()
    )

    await audit_service.log_action(event_id, "Candidate Registered", user_id, {
        "full_name": full_name,
        "role": role,
        "time": context.user_data.get("ob_time")
    })

    return ConversationHandler.END

async def handle_ob_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Возврат к началу регистрации (к выбору роли)."""
    # UI-02: Очищаем устаревшие данные в user_data
    for key in ["ob_role", "ob_phone", "ob_full_name", "ob_time", "ob_gender"]:  # BUG-2 FIX: added ob_gender
        context.user_data.pop(key, None)
    
    event_id = context.user_data.get("ob_event_id")
    event = await event_service.get_event(event_id)
    roles = event.required_roles or ["Промоутер", "Хостес", "Регистратор"]
    
    from utils.keyboards import get_onboarding_role_reply_keyboard
    await update.message.reply_html(
        "📝 <b>Шаг 1 из 5: Ваша роль</b>\n\nВыберите позицию:",
        reply_markup=get_onboarding_role_reply_keyboard(roles)
    )
    return CHOOSE_ROLE

def get_onboarding_handler():
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(handle_ob_start, pattern="^ob_start:")
        ],
        states={
            WAIT_REG_START: [CallbackQueryHandler(handle_ob_start, pattern=r"^ob_start:")],
            CHOOSE_ROLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_role_choice)],
            SHARE_PHONE: [MessageHandler(filters.CONTACT, handle_phone_input)],
            INPUT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_name_input)],
            CHOOSE_GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_gender_choice)],
            CHOOSE_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_time_choice)],
            CONFIRM_DATA: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_ob_confirm_action)]
        },
        fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)],
        allow_reentry=True,
        name="candidate_onboarding",
        persistent=True
    )
