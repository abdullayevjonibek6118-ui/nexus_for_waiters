"""
Nexus AI — Утилиты: Inline-клавиатуры
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from utils.constants import VoteStatus


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


def get_gender_inline_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора пола (Inline)."""
    keyboard = [
        [
            InlineKeyboardButton("👨 Мужской", callback_data="set_gender:Male"),
            InlineKeyboardButton("👩 Женский", callback_data="set_gender:Female"),
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
        emoji = {VoteStatus.YES: "✅", VoteStatus.MAYBE: "🤔", VoteStatus.NO: "❌"}.get(vote, "❓")
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


def get_role_selection_keyboard():
    """Reply-клавиатура выбора роли."""
    from telegram import ReplyKeyboardMarkup
    keyboard = [
        ["👨‍💼 Я Рекрутер (Company Admin)"],
        ["🙋‍♂️ Я Кандидат (Waiter)"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)


# ─── Новые клавиатуры для SaaS сценария ───────────────────────────────────────

def get_onboarding_start_keyboard(event_id: str) -> InlineKeyboardMarkup:
    """Этап 2 — Кнопка 'Начать регистрацию'."""
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🚀 Начать регистрацию", callback_data=f"ob_start:{event_id}")
    ]])


def get_dynamic_choice_keyboard(items: list[str], prefix: str, omit_event_id: bool = True) -> InlineKeyboardMarkup:
    """Универсальная клавиатура для выбора роли или времени."""
    keyboard = []
    for item in items:
        keyboard.append([InlineKeyboardButton(item, callback_data=f"{prefix}:{item}")])
    return InlineKeyboardMarkup(keyboard)


def get_onboarding_confirm_keyboard(event_id: str) -> InlineKeyboardMarkup:
    """Этап 7 — Подтверждение данных."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Подтвердить", callback_data=f"ob_confirm:{event_id}")],
        [InlineKeyboardButton("✏️ Изменить", callback_data=f"ob_edit:{event_id}")]
    ])


def get_invitation_keyboard(event_id: str) -> InlineKeyboardMarkup:
    """Этап 9 — Клавиатура приглашения."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Подтвердить участие", callback_data=f"inv_yes:{event_id}")],
        [InlineKeyboardButton("❌ Отказаться", callback_data=f"inv_no:{event_id}")]
    ])


def get_onboarding_role_reply_keyboard(roles: list[str]):
    """Reply-клавиатура выбора роли."""
    from telegram import ReplyKeyboardMarkup
    keyboard = [[r] for r in roles]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)


def get_onboarding_gender_reply_keyboard():
    """Reply-клавиатура выбора пола."""
    from telegram import ReplyKeyboardMarkup
    keyboard = [["👨 Мужской", "👩 Женский"]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)


def get_onboarding_time_reply_keyboard(times: list[str]):
    """Reply-клавиатура выбора времени."""
    from telegram import ReplyKeyboardMarkup
    keyboard = [[t] for t in times]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)


def get_onboarding_confirm_reply_keyboard():
    """Reply-клавиатура подтверждения регистрации."""
    from telegram import ReplyKeyboardMarkup
    keyboard = [["✅ Подтвердить"], ["✏️ Изменить"]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)


def get_checkin_keyboard(event_id: str) -> InlineKeyboardMarkup:
    """Кнопка 'Я пришел' для кандидата."""
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("📍 Я на месте / Начать смену", callback_data=f"checkin_start:{event_id}")
    ]])


def get_recruiter_dashboard_keyboard():
    """Главная Reply-клавиатура рекрутера."""
    from telegram import ReplyKeyboardMarkup
    keyboard = [
        ["🆕 Создать мероприятие", "📋 Мои мероприятия"],
        ["📊 Отчеты", "❓ Помощь"],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_events_list_reply_keyboard(events: list):
    """Reply-клавиатура со списком мероприятий (для выбора)."""
    from telegram import ReplyKeyboardMarkup
    keyboard = []
    for ev in events:
        label = f"📅 {ev.date} | {ev.title}"
        keyboard.append([label])
    keyboard.append(["⬅️ Назад в меню"])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_event_action_reply_keyboard(event_title: str):
    """Reply-клавиатура действий с выбранным мероприятием."""
    from telegram import ReplyKeyboardMarkup
    keyboard = [
        ["📢 Опубликовать", "👥 Карточки"],
        ["✉️ Уведомить", "📄 Экспорт Excel"],
        ["⏰ Назначить время", "🤖 Автоотбор"],
        ["📊 Логи", "❌ Архивировать"],
        ["⬅️ К списку мероприятий"],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_candidate_card_keyboard():
    """Reply-клавиатура управления карточками (Этап 5)."""
    from telegram import ReplyKeyboardMarkup
    keyboard = [
        ["✅ Принять", "❌ Отклонить"],
        ["➡️ Следующий"],
        ["⬅️ Назад к управлению"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_event_post_creation_keyboard():
    """Reply-клавиатура после создания мероприятия."""
    from telegram import ReplyKeyboardMarkup
    keyboard = [
        ["📢 Опубликовать", "👥 Карточки"],
        ["✉️ Уведомить", "📄 Экспорт Excel"],
        ["🤖 Автоотбор", "⬅️ К списку"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_set_times_keyboard(selected_candidates: list, event_id: str) -> InlineKeyboardMarkup:
    """Клавиатура для назначения времени (упрощенная)."""
    keyboard = [
        [InlineKeyboardButton("⏰ Назначить всем одинаковое время", callback_data=f"st_all:{event_id}")]
    ]
    for c in selected_candidates:
        profile = c.get("candidates", {}) or {}
        full_name = f"{profile.get('first_name', '')} {profile.get('last_name', '')}".strip()
        user_id = c.get("user_id")
        keyboard.append([
            InlineKeyboardButton(f"👤 {full_name}", callback_data=f"st_one:{event_id}:{user_id}")
        ])
    return InlineKeyboardMarkup(keyboard)
