"""
Nexus AI — Утилиты: Inline-клавиатуры
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def get_event_keyboard(event_id: str) -> InlineKeyboardMarkup:
    """Клавиатура действий с мероприятием."""
    keyboard = [
        [
            InlineKeyboardButton("📊 Опубликовать опрос", callback_data=f"poll_publish:{event_id}"),
        ],
        [
            InlineKeyboardButton("👥 Выбрать кандидатов", callback_data=f"select:{event_id}"),
            InlineKeyboardButton("⏰ Назначить время", callback_data=f"times:{event_id}"),
        ],
        [
            InlineKeyboardButton("📋 Создать таблицу", callback_data=f"sheet:{event_id}"),
            InlineKeyboardButton("✉️ Уведомить кандидатов", callback_data=f"notify:{event_id}"),
        ],
        [
            InlineKeyboardButton("📝 Логи", callback_data=f"logs:{event_id}"),
            InlineKeyboardButton("📄 Excel", callback_data=f"export_excel:{event_id}"),
        ],
        [
            InlineKeyboardButton("❌ Архивировать", callback_data=f"close:{event_id}"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_confirm_keyboard(event_id: str) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения участия для кандидата."""
    keyboard = [
        [
            InlineKeyboardButton("✅ Подтверждаю участие", callback_data=f"confirm_yes:{event_id}"),
        ],
        [
            InlineKeyboardButton("❌ Не смогу прийти", callback_data=f"confirm_no:{event_id}"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_gender_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора пола."""
    keyboard = [
        [
            InlineKeyboardButton("М", callback_data="set_gender:Male"),
            InlineKeyboardButton("Ж", callback_data="set_gender:Female"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_candidate_select_keyboard(
    candidates: list, event_id: str
) -> InlineKeyboardMarkup:
    """Клавиатура выбора кандидатов из списка проголосовавших."""
    keyboard = []
    for c in candidates:
        profile = c.get("candidates", {}) or {}
        full_name = f"{profile.get('first_name', '')} {profile.get('last_name', '')}".strip()
        vote = c.get("vote_status", "?")
        emoji = {"yes": "✅", "maybe": "🤔", "no": "❌"}.get(vote, "❓")
        user_id = c.get("user_id")
        keyboard.append([
            InlineKeyboardButton(
                f"{emoji} {full_name}",
                callback_data=f"toggle_select:{event_id}:{user_id}"
            )
        ])
    keyboard.append([
        InlineKeyboardButton("💾 Сохранить выбор", callback_data=f"save_selection:{event_id}")
    ])
    return InlineKeyboardMarkup(keyboard)


def get_back_keyboard(callback_data: str = "back") -> InlineKeyboardMarkup:
    """Кнопка «Назад»."""
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data=callback_data)]])


def get_events_list_keyboard(events: list) -> InlineKeyboardMarkup:
    """Клавиатура со списком мероприятий для управления."""
    keyboard = []
    for ev in events:
        btn_text = f"📅 {ev.date} | {ev.title}"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"manage:{ev.event_id}")])
    return InlineKeyboardMarkup(keyboard)
