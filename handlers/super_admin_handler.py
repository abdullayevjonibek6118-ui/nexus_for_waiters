"""
Nexus AI — Super Admin Handler
Панель владельца платформы (SaaS)
Команды: /owner
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from config import settings
from services import company_service, recruiter_service
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Состояния
CREATE_COMPANY, SET_FEE, ADD_RECRUITER_ID, SET_SUBSCRIPTION, SET_GROUP_ID = range(5)

def is_super_admin(user_id: int) -> bool:
    return user_id == settings.super_admin_id

async def owner_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Главная панель владельца."""
    if not is_super_admin(update.effective_user.id):
        return

    keyboard = [
        [InlineKeyboardButton("🏢 Создать компанию", callback_data="sa:create_company")],
        [InlineKeyboardButton("📋 Список компаний", callback_data="sa:list_companies")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_html(
        "👑 <b>Панель владельца Nexus AI</b>\n\n"
        "Управляйте компаниями, рекрутерами и подписками.",
        reply_markup=reply_markup
    )

async def sa_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка простых нажатий в админке."""
    query = update.callback_query
    if not is_super_admin(update.effective_user.id):
        await query.answer("⛔ Нет доступа.")
        return

    await query.answer()
    data = query.data

    if data == "sa:list_companies":
        companies = await company_service.list_companies()
        if not companies:
            await query.edit_message_text("📭 Компаний пока нет.")
            return

        text = "🏢 <b>Список компаний:</b>\n\n"
        keyboard = []
        for c in companies:
            status = "✅" if c["status"] == "active" else "❌"
            text += f"{status} {c['name']} | ID: <code>{c['id'][:8]}</code>\n"
            keyboard.append([InlineKeyboardButton(f"⚙️ {c['name']}", callback_data=f"sa:manage:{c['id']}")])
        
        keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="sa:main")])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

    elif data.startswith("sa:manage:"):
        company_id = data.split(":")[2]
        company = await company_service.get_company(company_id)
        recruiters = await recruiter_service.list_company_recruiters(company_id)
        
        text = (
            f"🏢 <b>Компания: {company['name']}</b>\n"
            f"🆔 ID: <code>{company['id']}</code>\n"
            f"💰 Плата: {company['monthly_fee']} руб/мес\n"
            f"📅 Подписка до: {company['subscription_until'] or 'не задана'}\n"
            f"👥 Рекрутеров: {len(recruiters)}\n"
            f"📊 Статус: {company['status']}"
        )
        
        keyboard = [
            [InlineKeyboardButton("➕ Добавить рекрутера", callback_data=f"sa:add_rec:{company_id}")],
            [InlineKeyboardButton("📅 Продлить подписку", callback_data=f"sa:sub:{company_id}")],
            [InlineKeyboardButton("💬 Указать ID группы", callback_data=f"sa:set_group:{company_id}")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="sa:list_companies")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

    elif data == "sa:main":
        keyboard = [
            [InlineKeyboardButton("🏢 Создать компанию", callback_data="sa:create_company")],
            [InlineKeyboardButton("📋 Список компаний", callback_data="sa:list_companies")],
        ]
        await query.edit_message_text("👑 <b>Панель владельца Nexus AI</b>", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

# --- Conversation Flow для создания компании ---

async def create_company_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Введите название новой компании:")
    return CREATE_COMPANY

async def company_name_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["sa_comp_name"] = update.message.text.strip()
    await update.message.reply_text("Введите ежемесячную плату (например, 5000):")
    return SET_FEE

async def company_fee_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        fee = float(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("Введите число!")
        return SET_FEE
        
    name = context.user_data.get("sa_comp_name")
    company = await company_service.create_company(name, fee)
    
    if company:
        await update.message.reply_html(f"✅ Компания <b>{name}</b> создана!\nID: <code>{company['id']}</code>")
    else:
        await update.message.reply_text("❌ Ошибка при создании.")
    
    return ConversationHandler.END

# --- Flow для добавления рекрутера ---

async def add_recruiter_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    company_id = query.data.split(":")[2]
    context.user_data["sa_target_comp"] = company_id
    await query.edit_message_text("Введите Telegram User ID рекрутера (число):")
    return ADD_RECRUITER_ID

async def recruiter_id_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        user_id = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("Введите корректный ID (число):")
        return ADD_RECRUITER_ID
        
    company_id = context.user_data.get("sa_target_comp")
    res = await recruiter_service.add_recruiter(user_id, company_id)
    
    if res:
        await update.message.reply_text(f"✅ Рекрутер {user_id} добавлен в компанию.")
    else:
        await update.message.reply_text("❌ Ошибка при добавлении.")
    
    return ConversationHandler.END

# --- Продление подписки ---

async def extend_sub_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    company_id = query.data.split(":")[2]
    context.user_data["sa_target_comp"] = company_id
    await query.edit_message_text("На сколько месяцев продлить подписку? (введите число 1-12):")
    return SET_SUBSCRIPTION

async def sub_months_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        months = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("Введите число месяцев!")
        return SET_SUBSCRIPTION
        
    company_id = context.user_data.get("sa_target_comp")
    until = datetime.now() + timedelta(days=30 * months)
    res = await company_service.update_subscription(company_id, until)
    
    if res:
        await update.message.reply_text(f"✅ Подписка продлена до {until.strftime('%d.%m.%Y')}")
    else:
        await update.message.reply_text("❌ Ошибка.")
        
    return ConversationHandler.END

# --- Установка ID группы ---

async def set_group_id_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    company_id = query.data.split(":")[2]
    context.user_data["sa_target_comp"] = company_id
    await query.edit_message_text("Введите Telegram Chat ID группы для этой компании (отрицательное число для супергрупп):")
    return SET_GROUP_ID

async def group_id_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        group_id = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("Введите корректный Chat ID (число):")
        return SET_GROUP_ID
        
    company_id = context.user_data.get("sa_target_comp")
    from database import supabase
    res = supabase.table("companies").update({"group_chat_id": group_id}).eq("id", company_id).execute()
    
    if res.data:
        await update.message.reply_text(f"✅ ID группы {group_id} сохранён для компании.")
    else:
        await update.message.reply_text("❌ Ошибка.")
    
    return ConversationHandler.END

async def cancel_sa(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Отменено.")
    return ConversationHandler.END

def get_super_admin_handler():
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(create_company_start, pattern="^sa:create_company"),
            CallbackQueryHandler(add_recruiter_start, pattern="^sa:add_rec:"),
            CallbackQueryHandler(extend_sub_start, pattern="^sa:sub:"),
            CallbackQueryHandler(set_group_id_start, pattern="^sa:set_group:"),
        ],
        states={
            CREATE_COMPANY: [MessageHandler(filters.TEXT & ~filters.COMMAND, company_name_received)],
            SET_FEE: [MessageHandler(filters.TEXT & ~filters.COMMAND, company_fee_received)],
            ADD_RECRUITER_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, recruiter_id_received)],
            SET_SUBSCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, sub_months_received)],
            SET_GROUP_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, group_id_received)],
        },
        fallbacks=[CommandHandler("cancel", cancel_sa)],
        allow_reentry=True
    )
