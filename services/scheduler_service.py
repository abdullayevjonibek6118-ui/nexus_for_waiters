"""
Nexus AI — Scheduler Service
Планирование напоминаний об оплате и других задач
"""
import logging
import pytz
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.triggers.cron import CronTrigger
from config import settings
from services import event_service, candidate_service

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


def get_scheduler() -> AsyncIOScheduler:
    """Singleton планировщика задач."""
    global _scheduler
    if _scheduler is None:
        tz = pytz.timezone(settings.timezone)
        _scheduler = AsyncIOScheduler(
            jobstores={"default": MemoryJobStore()},
            timezone=tz,
        )
    return _scheduler

async def get_scheduler_async() -> AsyncIOScheduler:
    """Инициализация и запуск планировщика внутри event loop."""
    scheduler = get_scheduler()
    if not scheduler.running:
        scheduler.start()
        logger.info(f"Планировщик запущен (timezone={settings.timezone})")
    return scheduler


async def schedule_payment_reminder(
    event_id: str,
    event_title: str,
    bot,
    admin_ids: list,
    days: int = 14,
) -> str:
    """
    Запланировать напоминание рекрутеру об оплате через N дней.
    Возвращает job_id.
    """
    scheduler = get_scheduler()
    run_at = datetime.now(tz=pytz.timezone(settings.timezone)) + timedelta(days=days)
    job_id = f"payment_reminder_{event_id}"

    async def _send_reminder():
        text = (
            f"💰 <b>Напоминание об оплате</b>\n\n"
            f"Мероприятие: <b>{event_title}</b>\n"
            f"Прошло {days} дней. Пожалуйста, подтвердите оплату.\n\n"
            f"Используйте: /payment_confirmed {event_id}"
        )
        for admin_id in admin_ids:
            try:
                await bot.send_message(chat_id=admin_id, text=text, parse_mode="HTML")
            except Exception as e:
                logger.error(f"Ошибка отправки напоминания {admin_id}: {e}")

    scheduler.add_job(
        _send_reminder,
        trigger="date",
        run_date=run_at,
        id=job_id,
        replace_existing=True,
    )
    logger.info(f"Напоминание об оплате запланировано: {run_at} (job_id={job_id})")
    return job_id


def cancel_reminder(job_id: str) -> bool:
    """Отменить запланированную задачу."""
    try:
        scheduler = get_scheduler()
        scheduler.remove_job(job_id)
        logger.info(f"Задача {job_id} отменена")
        return True
    except Exception as e:
        logger.error(f"Ошибка отмены задачи {job_id}: {e}")
        return False


async def schedule_daily_reminders(bot):
    """
    Запускает крон для проверки мероприятий 'на завтра'.
    """
    scheduler = get_scheduler()
    job_id = "daily_tomorrow_reminders"

    async def _check_tomorrow_events():
        logger.info("Запуск проверки мероприятий на завтра...")
        tz = pytz.timezone(settings.timezone)
        tomorrow = (datetime.now(tz) + timedelta(days=1)).strftime("%Y-%m-%d")

        # Получаем все активные мероприятия
        events = await event_service.get_active_events()
        for ev in events:
            if ev.date == tomorrow:
                # Нашли мероприятие на завтра, берём подтвержденных кандидатов
                selected = await candidate_service.get_selected_candidates(ev.event_id)
                count = 0
                for c in selected:
                    if c.get("confirmed"):
                        user_id = c.get("user_id")
                        arrival = c.get("arrival_time", "—")
                        text = (
                            f"🔔 <b>Напоминание о мероприятии ЗАВТРА!</b>\n\n"
                            f"📌 <b>{ev.title}</b>\n"
                            f"📍 Место: {ev.location}\n"
                            f"⏰ Время прихода: {arrival}\n\n"
                            f"Ждём вас!"
                        )
                        try:
                            await bot.send_message(chat_id=user_id, text=text, parse_mode="HTML")
                            count += 1
                        except Exception as e:
                            logger.error(f"Ошибка отправки напоминания {user_id}: {e}")
                logger.info(f"Напоминания отправлены {count} кандидатам для {ev.title} ({ev.event_id})")

    # Запуск каждый день в 18:00 по времени бота
    scheduler.add_job(
        _check_tomorrow_events,
        trigger=CronTrigger(hour=18, minute=0, timezone=pytz.timezone(settings.timezone)),
        id=job_id,
        replace_existing=True,
    )
    logger.info(f"Крон на ежедневные напоминания добавлен (18:00 {settings.timezone})")
