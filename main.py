"""
Nexus AI Telegram Bot — Точка входа
Регистрация всех хендлеров и запуск бота.
"""
import logging
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    PollAnswerHandler,
    filters,
)
from config import settings

# Хендлеры
from handlers.start import start_command, help_command
from handlers.event_handler import (
    get_create_event_handler, 
    list_events, 
    handle_event_action_callback, 
    events_dashboard,
    handle_recruiter_menu,
    handle_event_selection,
    handle_event_menu_action
)
from handlers.onboarding_handler import get_onboarding_handler
from handlers.poll_handler import publish_poll, close_poll
from handlers.candidate_handler import (
    list_voters,
    show_candidate_cards,
    set_times_cmd,
    notify_candidates_cmd,
    handle_candidate_confirmation,
    handle_contact,
    handle_set_gender,
    handle_set_time_callback,
    handle_time_message_input,
    handle_card_callback,
    handle_card_action,
    handle_checkin,
    handle_confirm_checkin_callback,
    handle_auto_select_input,
    handle_general_name_input,
)
from handlers.admin_handler import (
    create_sheet_cmd,
    payment_reminder_cmd,
    payment_confirmed_cmd,
    logs_cmd,
    close_event_cmd,
    export_excel_cmd,
    announce_cmd,
)
from handlers.super_admin_handler import owner_cmd, get_super_admin_handler, sa_callback_handler
from handlers.role_handler import handle_role_callback, handle_role_selection

# Планировщик (инициализация)
from services.scheduler_service import get_scheduler, get_scheduler_async


def setup_logging():
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logging.basicConfig(
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        level=log_level,
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    # Уменьшим шуm от httpx
    logging.getLogger("httpx").setLevel(logging.WARNING)


def main() -> None:
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("🚀 Запуск Nexus AI Bot...")

    async def on_startup(app):
        """Запускается после старта event loop — безопасное место для планировщика."""
        await get_scheduler_async()
        
        # Добавляем крон-задачу для ежедневных напоминаний
        from services.scheduler_service import schedule_daily_reminders
        await schedule_daily_reminders(app.bot)
        
        logger.info("✅ Планировщик задач запущен")

    # Создать приложение с увеличенными таймаутами
    app = (
        Application.builder()
        .token(settings.bot_token)
        .post_init(on_startup)
        .connect_timeout(30)
        .read_timeout(60)
        .write_timeout(60)
        .build()
    )

    # ── Базовые команды ──────────────────────────────────────────────────────
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))

    # ── Мероприятия ─────────────────────────────────────────────────────────
    app.add_handler(get_create_event_handler())           # ConversationHandler
    app.add_handler(get_onboarding_handler())             # Onboarding
    app.add_handler(CommandHandler("events", events_dashboard))
    app.add_handler(CommandHandler("list_events", list_events))

    # ── Опросы ──────────────────────────────────────────────────────────────
    app.add_handler(CommandHandler("publish_poll", publish_poll))
    app.add_handler(CommandHandler("close_poll", close_poll))

    # ── Кандидаты ───────────────────────────────────────────────────────────
    app.add_handler(CommandHandler("voters", list_voters))
    app.add_handler(CommandHandler("candidates", show_candidate_cards))
    app.add_handler(CommandHandler("set_times", set_times_cmd))
    app.add_handler(CommandHandler("notify_candidates", notify_candidates_cmd))

    # ── Администратор ────────────────────────────────────────────────────────
    app.add_handler(CommandHandler("create_sheet", create_sheet_cmd))
    app.add_handler(CommandHandler("payment_reminder", payment_reminder_cmd))
    app.add_handler(CommandHandler("payment_confirmed", payment_confirmed_cmd))
    app.add_handler(CommandHandler("logs", logs_cmd))
    app.add_handler(CommandHandler("export_excel", export_excel_cmd))
    app.add_handler(CommandHandler("announce", announce_cmd))
    
    # ── Владелец (SaaS) ──────────────────────────────────────────────────────
    app.add_handler(CommandHandler("owner", owner_cmd))
    app.add_handler(get_super_admin_handler()) # ConversationHandler для создания компаний

    # ── Callback-кнопки ─────────────────────────────────────────────────────
    app.add_handler(CallbackQueryHandler(handle_candidate_confirmation, pattern=r"^(confirm|inv)_(yes|no):"))
    app.add_handler(CallbackQueryHandler(
        handle_event_action_callback,
        pattern=r"^(poll_publish|select|times|sheet|notify|logs|close|manage|export_excel|ev_[a-zA-Z0-9_]+)(:|$)"
    ))
    app.add_handler(CallbackQueryHandler(handle_card_callback, pattern=r"^card_(accept|reject|next)"))
    app.add_handler(CallbackQueryHandler(handle_checkin, pattern=r"^checkin_"))
    app.add_handler(CallbackQueryHandler(handle_confirm_checkin_callback, pattern=r"^c_chk:"))
    app.add_handler(CallbackQueryHandler(handle_set_gender, pattern=r"^set_gender:"))
    app.add_handler(CallbackQueryHandler(handle_role_callback, pattern=r"^role:"))
    app.add_handler(CallbackQueryHandler(sa_callback_handler, pattern=r"^sa:"))
    app.add_handler(CallbackQueryHandler(handle_set_time_callback, pattern=r"^st_(all|one):"))

    # ── Неизвестные команды & Текстовые кнопки ──────────────────────────────
    # Группы приоритетов для обработки Reply-кнопок
    app.add_handler(MessageHandler(
        filters.Regex(r"^(👨‍💼 Я Рекрутер|🙋‍♂️ Я Кандидат)"),
        handle_role_selection
    ), group=0)

    app.add_handler(MessageHandler(
        filters.Regex(r"^(🆕 Создать мероприятие|📋 Мои мероприятия|📊 Отчеты|❓ Помощь)$"),
        handle_recruiter_menu
    ), group=0)
    
    app.add_handler(MessageHandler(
        filters.Regex(r"^(📅|⬅️ Назад в меню)"),
        handle_event_selection
    ), group=0)
    
    app.add_handler(MessageHandler(
        filters.Regex(r"^(📢 Опубликовать|👥 Карточки|✉️ Уведомить|📄 Экспорт Excel|⏰ Назначить время|🤖 Автоотбор|📊 Логи|❌ Архивировать|⬅️ К списку мероприятий)"),
        handle_event_menu_action
    ), group=0)

    app.add_handler(MessageHandler(
        filters.Regex(r"^(✅ Принять|❌ Отклонить|➡️ Следующий|⬅️ Назад к управлению)"),
        handle_card_action
    ), group=0)

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_auto_select_input), group=1)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_time_message_input), group=2)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_general_name_input), group=3)
    app.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    app.add_handler(MessageHandler(
        filters.COMMAND,
        lambda u, c: u.message.reply_text("❓ Неизвестная команда. Используйте /help")
    ))

    logger.info("✅ Все хендлеры зарегистрированы. Запуск polling...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
