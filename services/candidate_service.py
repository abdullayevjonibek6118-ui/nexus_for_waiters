"""
Nexus AI — Candidate Service
Управление профилями кандидатов и связками EventCandidate
"""
import logging
from typing import Optional, List
from database import get_db
from models.candidate import Candidate, VoteStatus
from models.event_candidate import EventCandidate

logger = logging.getLogger(__name__)


async def get_or_create_candidate(user_id: int, first_name: str,
                                   last_name: Optional[str] = None,
                                   username: Optional[str] = None) -> Candidate:
    """Получить существующего или создать нового кандидата."""
    try:
        db = get_db()
        result = db.table("candidates").select("*").eq("user_id", user_id).execute()
        if result.data:
            # Обновляем существующего кандидата (например, если сменил ник)
            db.table("candidates").update({
                "first_name": first_name,
                "last_name": last_name or "",
                "telegram_username": username or ""
            }).eq("user_id", user_id).execute()
            return Candidate(**result.data[0])

        # Создать нового кандидата
        new_candidate = {
            "user_id": user_id,
            "first_name": first_name,
            "last_name": last_name or "",
            "full_name": "",
            "primary_role": "",
            "telegram_username": username or "",
            "has_messaged_bot": True,
        }
        db.table("candidates").insert(new_candidate).execute()
        return Candidate(**new_candidate)
    except Exception as e:
        logger.error(f"Ошибка get_or_create_candidate для {user_id}: {e}")
        return Candidate(user_id=user_id, first_name=first_name)


async def update_phone_number(user_id: int, phone: str) -> bool:
    """Сохранить номер телефона кандидата."""
    try:
        db = get_db()
        db.table("candidates").update({"phone_number": phone}).eq("user_id", user_id).execute()
        return True
    except Exception as e:
        logger.error(f"Ошибка сохранения телефона для {user_id}: {e}")
        return False


async def update_candidate_gender(user_id: int, gender: str) -> bool:
    """Установить пол кандидата (Male/Female)."""
    try:
        db = get_db()
        db.table("candidates").update({"gender": gender}).eq("user_id", user_id).execute()
        return True
    except Exception as e:
        logger.error(f"Ошибка сохранения пола кандидата {user_id}: {e}")
        return False


async def save_vote(event_id: str, user_id: int, vote_status: VoteStatus) -> bool:
    """Сохранить голос кандидата за мероприятие."""
    try:
        db = get_db()
        existing = (
            db.table("event_candidates")
            .select("id")
            .eq("event_id", event_id)
            .eq("user_id", user_id)
            .execute()
        )
        if existing.data:
            db.table("event_candidates").update(
                {"vote_status": vote_status.value}
            ).eq("event_id", event_id).eq("user_id", user_id).execute()
        else:
            db.table("event_candidates").insert({
                "event_id": event_id,
                "user_id": user_id,
                "vote_status": vote_status.value,
                "selected": False,
                "confirmed": False,
            }).execute()
        return True
    except Exception as e:
        logger.error(f"Ошибка сохранения голоса: {e}")
        return False


async def get_voters(event_id: str) -> List[dict]:
    """Получить всех, кто проголосовал за мероприятие."""
    try:
        db = get_db()
        result = (
            db.table("event_candidates")
            .select("*, candidates(first_name, last_name, phone_number, telegram_username)")
            .eq("event_id", event_id)
            .neq("vote_status", VoteStatus.NO.value)
            .execute()
        )
        return result.data or []
    except Exception as e:
        logger.error(f"Ошибка получения голосующих: {e}")
        return []


async def get_event_candidate(event_id: str, user_id: int) -> dict:
    """Получить заявку конкретного кандидата на мероприятие."""
    try:
        db = get_db()
        result = (
            db.table("event_candidates")
            .select("*")
            .eq("event_id", event_id)
            .eq("user_id", user_id)
            .execute()
        )
        if result.data:
            return result.data[0]
        return {}
    except Exception as e:
        logger.error(f"Ошибка получения заявки кандидата {user_id}: {e}")
        return {}


async def select_candidate(event_id: str, user_id: int, selected: bool = True) -> bool:
    """Пометить кандидата как выбранного/отмененного."""
    try:
        db = get_db()
        db.table("event_candidates").update(
            {"selected": selected}
        ).eq("event_id", event_id).eq("user_id", user_id).execute()
        return True
    except Exception as e:
        logger.error(f"Ошибка выбора кандидата {user_id}: {e}")
        return False


async def reset_event_selections(event_id: str) -> bool:
    """Сбросить статус `selected` для всех кандидатов мероприятия."""
    try:
        db = get_db()
        db.table("event_candidates").update(
            {"selected": False}
        ).eq("event_id", event_id).execute()
        return True
    except Exception as e:
        logger.error(f"Ошибка сброса выбора кандидатов для {event_id}: {e}")
        return False


async def get_selected_candidates(event_id: str) -> List[dict]:
    """Получить список выбранных кандидатов с профилями."""
    try:
        db = get_db()
        result = (
            db.table("event_candidates")
            .select("*, candidates(first_name, last_name, phone_number, telegram_username)")
            .eq("event_id", event_id)
            .eq("selected", True)
            .execute()
        )
        return result.data or []
    except Exception as e:
        logger.error(f"Ошибка получения выбранных кандидатов: {e}")
        return []


async def set_arrival_departure(event_id: str, user_id: int,
                                 arrival: str, departure: str) -> bool:
    """Установить время прихода и ухода кандидата."""
    try:
        db = get_db()
        db.table("event_candidates").update({
            "arrival_time": arrival,
            "departure_time": departure,
        }).eq("event_id", event_id).eq("user_id", user_id).execute()
        return True
    except Exception as e:
        logger.error(f"Ошибка установки времени для {user_id}: {e}")
        return False


async def confirm_candidate(event_id: str, user_id: int) -> bool:
    """Подтвердить участие кандидата."""
    try:
        db = get_db()
        db.table("event_candidates").update(
            {"confirmed": True}
        ).eq("event_id", event_id).eq("user_id", user_id).execute()
        return True
    except Exception as e:
        logger.error(f"Ошибка подтверждения кандидата {user_id}: {e}")
        return False


async def update_gender(user_id: int, gender: str) -> bool:
    """Сохранить пол кандидата."""
    try:
        db = get_db()
        db.table("candidates").update({"gender": gender}).eq("user_id", user_id).execute()
        return True
    except Exception as e:
        logger.error(f"Ошибка сохранения пола для {user_id}: {e}")
        return False


async def get_candidate_profile(user_id: int) -> Optional[Candidate]:
    """Получить профиль кандидата по user_id."""
    try:
        db = get_db()
        result = db.table("candidates").select("*").eq("user_id", user_id).execute()
        if result.data:
            return Candidate(**result.data[0])
        return None
    except Exception as e:
        logger.error(f"Ошибка получения профиля {user_id}: {e}")
        return None

async def update_candidate_full_name(user_id: int, full_name: str) -> bool:
    """Обновить ФИО кандидата."""
    try:
        db = get_db()
        db.table("candidates").update({"full_name": full_name}).eq("user_id", user_id).execute()
        return True
    except Exception as e:
        logger.error(f"Ошибка обновления ФИО для {user_id}: {e}")
        return False

async def update_candidate_role(user_id: int, role: str) -> bool:
    """Обновить роль кандидата."""
    try:
        db = get_db()
        db.table("candidates").update({"primary_role": role}).eq("user_id", user_id).execute()
        return True
    except Exception as e:
        logger.error(f"Ошибка обновления роли для {user_id}: {e}")
        return False

async def register_for_event(event_id: str, user_id: int, role: str, arrival_time: str) -> bool:
    """Зарегистрировать кандидата на конкретное мероприятие."""
    try:
        db = get_db()
        # Сначала сохраняем роль и время в связующую таблицу
        # Мы предполагаем, что запись в event_candidates уже есть (из-за голосования или просто создаем ее)
        res = db.table("event_candidates").upsert({
            "event_id": event_id,
            "user_id": user_id,
            "vote_status": "yes",
            "arrival_time": arrival_time,
            "selected": False, # Рекрутер должен будет подтвердить
        }).execute()
        
        # Также обновим основную роль кандидата, если она не задана
        cand = await get_candidate_profile(user_id)
        if cand and not cand.primary_role:
            await update_candidate_role(user_id, role)
            
        return True
    except Exception as e:
        logger.error(f"Ошибка регистрации на мероприятие: {e}")
        return False

async def mark_checked_in(event_id: str, user_id: int) -> bool:
    """Кандидат отметил, что пришел."""
    try:
        db = get_db()
        db.table("event_candidates").update({"is_checked_in": True}).eq("event_id", event_id).eq("user_id", user_id).execute()
        return True
    except Exception as e:
        logger.error(f"Ошибка mark_checked_in: {e}")
        return False

async def confirm_checkin(event_id: str, user_id: int) -> bool:
    """Рекрутер подтвердил приход."""
    try:
        db = get_db()
        db.table("event_candidates").update({"is_checkin_confirmed": True}).eq("event_id", event_id).eq("user_id", user_id).execute()
        return True
    except Exception as e:
        logger.error(f"Ошибка confirm_checkin: {e}")
        return False
