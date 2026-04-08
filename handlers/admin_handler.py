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
from services import (
    event_service, 
    candidate_service, 
    sheets_service, 
    audit_service, 
    scheduler_service, 
    recruiter_service,
    excel_service
)

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

    # Reload event data to ensure we have the latest channel_chat_id and channel_message_id
    event = await event_service.get_event(event_id)

    post_updated = False
    post_error = ""

    has_channel_data = (
        hasattr(event, 'channel_chat_id') and
        event.channel_chat_id and
        hasattr(event, 'channel_message_id') and
        event.channel_message_id
    )

    if has_channel_data:
        try:
            # Rebuild the EXACT same text format that publish_poll used, then append ЗАКРЫТО
            roles_text = "\n".join([f"• {r}" for r in (event.required_roles or [])])
            if not roles_text:
                roles_text = "• Промоутеры\n• Хостес\n• Регистраторы"

            times_text = ", ".join(event.arrival_times) if event.arrival_times else "Не указано"

            # Use the SAME format as publish_poll, then add ЗАКРЫТО
            closed_text = (
                "📢 <b>Работа на мероприятии</b>\n\n"
                f"<b>{event.title}</b>\n\n"
                f"📅 Дата: {event.date}\n"
                f"⏰ Начало: {times_text}\n"
                f"🏁 Конец: {event.end_time or '—'}\n"
                f"📍 Место: {event.location}\n"
                f"💰 Оплата: {event.payment or 'По договоренности'}\n\n"
                f"Нужны сотрудники:\n{roles_text}\n\n"
                "� Чтобы участвовать нажмите кнопку\n\n"
                "�🔴 <b>ЗАКРЫТО</b>"
            )

            # Parse chat_id — handle both string and int formats
            raw_chat_id = event.channel_chat_id
            raw_msg_id = event.channel_message_id

            logger.info(f"Attempting to edit message: chat_id={raw_chat_id}, message_id={raw_msg_id}")

            # Convert chat_id: try int first, fallback to string
            try:
                chat_id_val = int(raw_chat_id)
            except (ValueError, TypeError):
                chat_id_val = raw_chat_id

            # Convert message_id to int
            try:
                msg_id = int(raw_msg_id)
            except (ValueError, TypeError) as e:
                raise ValueError(f"Invalid message_id format: {raw_msg_id}") from e

            # Try editing text first
            try:
                await context.bot.edit_message_text(
                    chat_id=chat_id_val,
                    message_id=msg_id,
                    text=closed_text,
                    parse_mode="HTML",
                    reply_markup=None  # Remove the registration button
                )
                post_updated = True
                logger.info(f"Successfully edited message text for event {event_id}")
            except Exception as inner_e:
                error_str = str(inner_e)
                logger.warning(f"edit_message_text failed: {error_str}")
                # If message is media (has caption instead of text), edit caption
                if "There is no text in the message to edit" in error_str:
                    await context.bot.edit_message_caption(
                        chat_id=chat_id_val,
                        message_id=msg_id,
                        caption=closed_text,
                        parse_mode="HTML",
                        reply_markup=None  # Remove the registration button
                    )
                    post_updated = True
                    logger.info(f"Successfully edited message caption for event {event_id}")
                else:
                    raise inner_e

        except Exception as e:
            logger.error(f"Failed to update channel post for event {event_id}: {e}", exc_info=True)
            post_error = str(e)
    else:
        logger.warning(
            f"No channel data for event {event_id}. "
            f"channel_chat_id={getattr(event, 'channel_chat_id', 'MISSING')}, "
            f"channel_message_id={getattr(event, 'channel_message_id', 'MISSING')}"
        )
        post_error = "ID поста не найдено в базе данных. Убедитесь, что /publish_poll был выполнен успешно."

    status_msg = "\n🔹 <i>Пост в канале обновлен.</i>" if post_updated else f"\n⚠️ <i>Не удалось обновить пост ({post_error}).</i>"

    await update.effective_message.reply_html(
        f"✅ <b>Мероприятие закрыто (в архиве).</b>{status_msg}\n\n"
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
        logger.info(f"No selected candidates for {event_id}, trying all applicants.")
        selected = await candidate_service.get_applicants(event_id)
        
    if not selected:
        await update.effective_message.reply_text("❌ Нет данных для выгрузки (никто не подавал заявку).")
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

