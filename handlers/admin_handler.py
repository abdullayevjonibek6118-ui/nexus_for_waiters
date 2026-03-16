"""
Nexus AI — Handler: Администратор
Команды: /create_sheet, /payment_reminder, /payment_confirmed, /logs
"""
import os
import asyncio
import logging
from telegram import Update
from telegram.ext import ContextTypes, ApplicationBuilder
from telegram.constants import ParseMode
from config import settings
from utils.constants import ApplicationStatus, EventStatus

logger = logging.getLogger(__name__)


async def is_recruiter(user_id: int) -> bool:
    """Проверка прав: Владелец или Рекрутер."""
    if user_id == settings.super_admin_id:
        return True
    return await recruiter_service.is_recruiter(user_id)


async def create_sheet_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/create_sheet <event_id> — Создать Google Sheet для мероприятия."""
    if not await is_recruiter(update.effective_user.id):
        await update.effective_message.reply_text("⛔ У вас нет прав.")
        return
    if not context.args:
        await update.effective_message.reply_text("Использование: /create_sheet <event_id>")
        return

    event_id = context.args[0]
    event = await event_service.get_event(event_id)
    if not event:
        await update.effective_message.reply_text("❌ Мероприятие не найдено.")
        return

    # Изоляция данных: проверяем принадлежность мероприятия компании рекрутера
    if update.effective_user.id != settings.super_admin_id:
        recruiter = await recruiter_service.get_recruiter(update.effective_user.id)
        if not recruiter or str(recruiter.get("company_id")) != str(event.company_id):
            await update.effective_message.reply_text("⛔ Ошибка доступа: Это мероприятие принадлежит другой компании.")
            return

    await update.effective_message.reply_text("⏳ Создаю Google Sheet...")

    selected = await candidate_service.get_selected_candidates(event_id)
    sheet_url = await sheets_service.create_event_sheet(
        event_title=event.title,
        event_date=event.date,
        event_location=event.location,
        candidates=selected,
    )

    if sheet_url:
        await event_service.save_sheet_url(event_id, sheet_url)
        await audit_service.log_action(
            event_id, "sheet_created", update.effective_user.id,
            {"sheet_url": sheet_url}
        )
        await update.effective_message.reply_html(
            f"✅ <b>Google Sheet создана!</b>\n\n"
            f"📋 <a href='{sheet_url}'>Открыть таблицу</a>\n\n"
            f"В таблице: {len(selected)} кандидатов"
        )
    else:
        await update.effective_message.reply_text(
            "❌ Не удалось создать Google Sheet.\n"
            "Проверьте настройки в .env (GOOGLE_CREDENTIALS_FILE)."
        )


async def payment_reminder_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/payment_reminder <event_id> — Запланировать напоминание об оплате."""
    if not await is_recruiter(update.effective_user.id):
        await update.effective_message.reply_text("⛔ У вас нет прав.")
        return
    if not context.args:
        await update.effective_message.reply_text("Использование: /payment_reminder <event_id>")
        return

    event_id = context.args[0]
    event = await event_service.get_event(event_id)
    if not event:
        await update.effective_message.reply_text("❌ Мероприятие не найдено.")
        return

    # Изоляция данных
    if update.effective_user.id != settings.super_admin_id:
        recruiter = await recruiter_service.get_recruiter(update.effective_user.id)
        if not recruiter or str(recruiter.get("company_id")) != str(event.company_id):
            await update.effective_message.reply_text("⛔ Ошибка доступа.")
            return

    job_id = await scheduler_service.schedule_payment_reminder(
        event_id=event_id,
        event_title=event.title,
        bot=context.bot,
        admin_ids=settings.admin_ids,
        days=14,
    )
    await event_service.update_event_status(event_id, EventStatus.PAYMENT_PENDING)
    await audit_service.log_action(
        event_id, "payment_reminder_scheduled", update.effective_user.id,
        {"job_id": job_id, "days": 14}
    )

    await update.effective_message.reply_html(
        f"⏰ <b>Напоминание запланировано!</b>\n\n"
        f"Через 14 дней придёт напоминание об оплате.\n"
        f"Job ID: <code>{job_id}</code>\n\n"
        f"Когда оплата получена: /payment_confirmed {event_id}"
    )


async def payment_confirmed_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/payment_confirmed <event_id> — Отменить напоминание (оплата получена)."""
    if not await is_recruiter(update.effective_user.id):
        await update.effective_message.reply_text("⛔ У вас нет прав.")
        return
    if not context.args:
        await update.effective_message.reply_text("Использование: /payment_confirmed <event_id>")
        return

    event_id = context.args[0]
    event = await event_service.get_event(event_id)
    if not event:
        await update.effective_message.reply_text("❌ Мероприятие не найдено.")
        return

    # Изоляция данных
    if update.effective_user.id != settings.super_admin_id:
        recruiter = await recruiter_service.get_recruiter(update.effective_user.id)
        if not recruiter or str(recruiter.get("company_id")) != str(event.company_id):
            await update.effective_message.reply_text("⛔ Ошибка доступа.")
            return

    job_id = f"payment_reminder_{event_id}"
    scheduler_service.cancel_reminder(job_id)
    await event_service.update_event_status(event_id, EventStatus.SELECTION_COMPLETED)
    await audit_service.log_action(
        event_id, "payment_confirmed", update.effective_user.id, {}
    )

    await update.effective_message.reply_html(
        f"✅ <b>Оплата подтверждена!</b>\n"
        f"Напоминание отменено. Мероприятие завершено."
    )


async def logs_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/logs <event_id> — Просмотр аудит-лога мероприятия."""
    if not await is_recruiter(update.effective_user.id):
        await update.effective_message.reply_text("⛔ У вас нет прав.")
        return
    if not context.args:
        await update.effective_message.reply_text("Использование: /logs <event_id>")
        return

    event_id = context.args[0]
    
    # Изоляция данных
    if update.effective_user.id != settings.super_admin_id:
        event = await event_service.get_event(event_id)
        if not event:
            await update.effective_message.reply_text("❌ Мероприятие не найдено.")
            return
        recruiter = await recruiter_service.get_recruiter(update.effective_user.id)
        if not recruiter or str(recruiter.get("company_id")) != str(event.company_id):
            await update.effective_message.reply_text("⛔ Ошибка доступа.")
            return

    logs = await audit_service.get_event_logs(event_id, limit=15)
    if not logs:
        await update.effective_message.reply_text("📭 Нет записей в логе.")
        return

    text = f"📝 <b>Аудит-лог мероприятия</b>\n<code>{event_id[:12]}...</code>\n\n"
    for log in logs:
        ts = log.get("timestamp", "")[:19].replace("T", " ")
        action = log.get("action", "")
        by = log.get("performed_by", "?")
        text += f"🕐 {ts}\n   🔸 {action} (by {by})\n"

    await update.effective_message.reply_html(text)


async def close_event_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/close_event <event_id> — Закрыть/архивировать мероприятие."""
    if not await is_recruiter(update.effective_user.id):
        await update.effective_message.reply_text("⛔ У вас нет прав.")
        return
    if not context.args:
        await update.effective_message.reply_text("Использование: /close_event <event_id>")
        return

    event_id = context.args[0]
    event = await event_service.get_event(event_id)
    if not event:
        await update.effective_message.reply_text("❌ Мероприятие не найдено.")
        return

    # Изоляция данных
    if update.effective_user.id != settings.super_admin_id:
        recruiter = await recruiter_service.get_recruiter(update.effective_user.id)
        if not recruiter or str(recruiter.get("company_id")) != str(event.company_id):
            await update.effective_message.reply_text("⛔ Ошибка доступа.")
            return

    await event_service.update_event_status(event_id, EventStatus.CLOSED)
    await audit_service.log_action(event_id, "event_closed", update.effective_user.id, {})

    await update.effective_message.reply_html(
        f"✅ <b>Мероприятие закрыто (в архиве).</b>\n\n"
        f"Вы можете посмотреть логи: /logs {event_id}"
    )


async def export_excel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/export_excel <event_id> — Выгрузить данные в XLSX."""
    if not await is_recruiter(update.effective_user.id):
        await update.effective_message.reply_text("⛔ У вас нет прав.")
        return
    if not context.args:
        await update.effective_message.reply_text("Использование: /export_excel <event_id>")
        return

    event_id = context.args[0]
    event = await event_service.get_event(event_id)
    if not event:
        await update.effective_message.reply_text("❌ Мероприятие не найдено.")
        return

    # Изоляция данных
    if update.effective_user.id != settings.super_admin_id:
        recruiter = await recruiter_service.get_recruiter(update.effective_user.id)
        if not recruiter or str(recruiter.get("company_id")) != str(event.company_id):
            await update.effective_message.reply_text("⛔ Ошибка доступа.")
            return

    selected = await candidate_service.get_selected_candidates(event_id)
    if not selected:
        await update.effective_message.reply_text("❌ Нет данных для выгрузки (никто не выбран).")
        return

    await update.effective_message.reply_text("⏳ Генерирую Excel файл...")

    try:
        # Запускаем в отдельном потоке, чтобы не блокировать event loop
        filepath = await asyncio.to_thread(
            excel_service.generate_event_xlsx,
            event_title=event.title,
            event_date=event.date,
            event_location=event.location,
            candidates=selected
        )
    except Exception as e:
        logger.error(f"Ошибка при генерации Excel: {e}")
        await update.effective_message.reply_text(f"❌ Ошибка при генерации файла: {e}")
        return

    try:
        with open(filepath, "rb") as f:
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=f,
                filename=os.path.basename(filepath),
                caption=f"📊 Выгрузка: {event.title}",
                read_timeout=60,
                write_timeout=60,
                connect_timeout=30
            )
    except Exception as e:
        logger.error(f"Ошибка отправки Excel: {e}")
        await update.effective_message.reply_text(f"❌ Ошибка при отправке файла: {e}")
    finally:
        # Guarantee removal of temporary file
        if os.path.exists(filepath):
            os.remove(filepath)


async def announce_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/announce <event_id> <сообщение> — Массовая рассылка сообщений."""
    if not await is_recruiter(update.effective_user.id):
        await update.effective_message.reply_text("⛔ У вас нет прав.")
        return
    if len(context.args) < 2:
        await update.effective_message.reply_text("Использование: /announce <event_id> <текст сообщения>")
        return

    event_id = context.args[0]
    message_text = " ".join(context.args[1:])
    
    event = await event_service.get_event(event_id)
    if not event:
        await update.effective_message.reply_text("❌ Мероприятие не найдено.")
        return

    # Изоляция данных
    if update.effective_user.id != settings.super_admin_id:
        recruiter = await recruiter_service.get_recruiter(update.effective_user.id)
        if not recruiter or str(recruiter.get("company_id")) != str(event.company_id):
            await update.effective_message.reply_text("⛔ Ошибка доступа.")
            return

    selected = await candidate_service.get_selected_candidates(event_id)
    if not selected:
        await update.effective_message.reply_text("❌ Нет выбранных кандидатов для рассылки.")
        return

    sent, failed = 0, 0
    full_message = f"📢 <b>Объявление по {event.title}:</b>\n\n{message_text}"
    
    for c in selected:
        user_id = c.get("user_id")
        try:
            await context.bot.send_message(chat_id=user_id, text=full_message, parse_mode="HTML")
            sent += 1
        except Exception as e:
            logger.warning(f"Не удалось отправить рассылку {user_id}: {e}")
            failed += 1

    await audit_service.log_action(
        event_id, "mass_announcement_sent", update.effective_user.id,
        {"sent": sent, "failed": failed, "length": len(message_text)}
    )

    await update.effective_message.reply_html(
        f"✅ <b>Рассылка завершена!</b>\n"
        f"📤 Доставлено: <b>{sent}</b> | ❌ Ошибок: <b>{failed}</b>"
    )

