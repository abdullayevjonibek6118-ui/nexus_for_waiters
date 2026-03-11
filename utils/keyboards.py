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
def get_role_selection_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора роли при регистрации."""
    keyboard = [
        [InlineKeyboardButton("👨‍💼 Я Рекрутер (Company Admin)", callback_data="role:recruiter")],
        [InlineKeyboardButton("🙋‍♂️ Я Кандидат (Waiter)", callback_data="role:candidate")],
    ]
    return InlineKeyboardMarkup(keyboard)


# ─── Новые клавиатуры для SaaS сценария ───────────────────────────────────────

def get_onboarding_start_keyboard(event_id: str) -> InlineKeyboardMarkup:
    """Этап 2 — Кнопка 'Начать регистрацию'."""
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🚀 Начать регистрацию", callback_data=f"ob_start:{event_id}")
    ]])


def get_dynamic_choice_keyboard(items: list[str], prefix: str, omit_event_id: bool = True) -> InlineKeyboardMarkup:
    """Универсальная клавиатура для выбора роли или времени.
    Убрали передачу event_id, чтобы избежать ошибки Button_data_invalid (лимит 64 байта)."""
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


def get_checkin_keyboard(event_id: str) -> InlineKeyboardMarkup:
    """Кнопка 'Я пришел' для кандидата."""
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("📍 Я на месте / Начать смену", callback_data=f"checkin_start:{event_id}")
    ]])


def get_recruiter_dashboard_keyboard() -> InlineKeyboardMarkup:
    """Этап 1 — Главная панель рекрутера."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🆕 Создать мероприятие", callback_data="ev_create")],
        [InlineKeyboardButton("📅 Активные мероприятия", callback_data="ev_active")],
        [InlineKeyboardButton("📊 Отчеты", callback_data="ev_reports")]
    ])


def get_candidate_card_keyboard(event_id: str, candidate_id: int) -> InlineKeyboardMarkup:
    """Этап 5 — Карточка кандидата."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Принять", callback_data=f"card_accept:{event_id}:{candidate_id}"),
            InlineKeyboardButton("❌ Отклонить", callback_data=f"card_reject:{event_id}:{candidate_id}")
        ],
        [InlineKeyboardButton("➡️ Следующий", callback_data=f"card_next:{event_id}")]
    ])


def get_event_post_creation_keyboard(event_id: str) -> InlineKeyboardMarkup:
    """Этап 3 — Мероприятие создано."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Опубликовать в группу", callback_data=f"ev_publish:{event_id}")],
        [
            InlineKeyboardButton("👥 Карточки", callback_data=f"ev_cands:{event_id}"),
            InlineKeyboardButton("🤖 Автоотбор", callback_data=f"ev_select:{event_id}")
        ],
        [InlineKeyboardButton("⚙️ Настройки", callback_data=f"ev_settings:{event_id}")],
        [InlineKeyboardButton("⬅️ К списку мероприятий", callback_data="ev_active")]
    ])


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
