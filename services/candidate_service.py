"""
Nexus AI — Candidate Service
Управление профилями кандидатов и связками EventCandidate
"""
import logging
import asyncio
from typing import Optional, List
from database import get_db
from models.candidate import Candidate
from models.event_candidate import EventCandidate, ApplicationStatus, can_transition
from utils.constants import VoteStatus
from utils.exceptions import DatabaseError, NexusError

# ── Исключения ───────────────────────────────────────────────────────────────

class CandidateNotFoundError(NexusError):
    """Заявка не найдена."""
    pass

class InvalidStatusTransitionError(NexusError):
    """Попытка недопустимого перехода статуса заявки."""
    def __init__(self, current: ApplicationStatus, target: ApplicationStatus):
        self.current = current
        self.target = target
        super().__init__(
            f"Переход {current.value} → {target.value} не разрешён"
        )

logger = logging.getLogger(__name__)

# ── Единственный вход кандидата ───────────────────────────────────────────────

async def apply_for_event(
    event_id: str,
    user_id: int,
    role: str,
    arrival_time: str,
    departure_time: Optional[str] = None
) -> bool:
    """
    Регистрирует кандидата на мероприятие через онбординг.
    """
    try:
        db = get_db()
        # Используем upsert: если кандидат нажал "Участвовать" дважды — обновляем данные
        await asyncio.to_thread(
            lambda: db.table("event_candidates").upsert({
                "event_id": event_id,
                "user_id": user_id,
                "application_status": ApplicationStatus.PENDING.value,
                "role": role,
                "arrival_time": arrival_time,
                "departure_time": departure_time,
                # Старые поля для обратной совместимости
                "vote_status": VoteStatus.YES.value,
                "selected": False,
                "confirmed": False,
            }, on_conflict="event_id,user_id").execute()
        )
        return True
    except Exception as e:
        logger.error(f"apply_for_event error user={user_id} event={event_id}: {e}")
        raise DatabaseError(f"Ошибка регистрации на мероприятие: {e}")


async def transition_application(
    event_id: str,
    user_id: int,
    target_status: ApplicationStatus,
) -> bool:
    """
    Меняет статус заявки с проверкой допустимости перехода.
    """
    try:
        db = get_db()
        
        # Читаем текущий статус
        result = await asyncio.to_thread(
            lambda: db.table("event_candidates")
                .select("application_status")
                .eq("event_id", event_id)
                .eq("user_id", user_id)
                .execute()
        )
        
        if not result.data:
            raise CandidateNotFoundError(
                f"Заявка не найдена: user={user_id}, event={event_id}"
            )
        
        current = ApplicationStatus(result.data[0]["application_status"])
        
        # Проверяем допустимость перехода
        if not can_transition(current, target_status):
            raise InvalidStatusTransitionError(current, target_status)
        
        # Обновляем статус + синхронизируем старые поля
        update_data = {"application_status": target_status.value}
        if target_status == ApplicationStatus.ACCEPTED:
            update_data["selected"] = True
        elif target_status == ApplicationStatus.CONFIRMED:
            update_data["confirmed"] = True
        elif target_status == ApplicationStatus.CHECKED_IN:
            update_data["is_checked_in"] = True
            update_data["is_checkin_confirmed"] = True
        elif target_status in (ApplicationStatus.REJECTED, ApplicationStatus.DECLINED):
            update_data["selected"] = False
        
        await asyncio.to_thread(
            lambda: db.table("event_candidates")
                .update(update_data)
                .eq("event_id", event_id)
                .eq("user_id", user_id)
                .execute()
        )
        return True

    except (CandidateNotFoundError, InvalidStatusTransitionError):
        raise
    except Exception as e:
        logger.error(f"transition_application error: {e}")
        raise DatabaseError(f"Ошибка смены статуса: {e}")


async def record_poll_interest(event_id: str, user_id: int) -> bool:
    """
    Фиксирует интерес к мероприятию через опрос.
    НЕ создаёт запись в event_candidates.
    """
    try:
        # Профиль уже должен быть создан в хендлере
        logger.info(f"Poll interest: user={user_id}, event={event_id}")
        return True
    except Exception as e:
        logger.error(f"record_poll_interest error: {e}")
        return False

async def get_or_create_candidate(user_id: int, first_name: str,
                                   last_name: Optional[str] = None,
                                   username: Optional[str] = None) -> Candidate:
    """Получить существующего или создать нового кандидата."""
    try:
        db = get_db()
        result = db.table("candidates").select("*").eq("user_id", user_id).execute()
        if result.data:
            # Обновляем существующего кандидата
            db.table("candidates").update({
                "first_name": first_name,
                "last_name": last_name or "",
                "telegram_username": username or ""
            }).eq("user_id", user_id).execute()
            return Candidate(**result.data[0])

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
        raise DatabaseError(f"Ошибка при работе с профилем кандидата: {e}")

async def update_phone_number(user_id: int, phone: str) -> bool:
    """Сохранить номер телефона кандидата."""
    try:
        db = get_db()
        db.table("candidates").update({"phone_number": phone}).eq("user_id", user_id).execute()
        return True
    except Exception as e:
        logger.error(f"Ошибка сохранения телефона для {user_id}: {e}")
        raise DatabaseError(f"Ошибка сохранения телефона: {e}")

async def update_candidate_gender(user_id: int, gender: str) -> bool:
    """Установить пол кандидата (Male/Female)."""
    try:
        db = get_db()
        db.table("candidates").update({"gender": gender}).eq("user_id", user_id).execute()
        return True
    except Exception as e:
        logger.error(f"Ошибка сохранения пола кандидата {user_id}: {e}")
        raise DatabaseError(f"Ошибка сохранения пола: {e}")




async def get_applicants(
    event_id: str,
    status: ApplicationStatus | None = None,
) -> List[dict]:
    """
    Возвращает кандидатов, подавших заявку через онбординг.
    Заменяет get_voters().
    """
    try:
        db = get_db()
        query = (
            db.table("event_candidates")
            .select("application_status,role,arrival_time,departure_time,user_id,candidates(first_name,last_name,full_name,phone_number,telegram_username,gender,primary_role)")
            .eq("event_id", event_id)
        )
        
        if status is not None:
            query = query.eq("application_status", status.value)
        # Убрана фильтрация по role IS NOT NULL, чтобы видеть всех кандидатов (в т.ч. из старых опросов)
        
        result = await asyncio.to_thread(lambda: query.execute())
        return result.data or []
    except Exception as e:
        logger.error(f"get_applicants error event={event_id}: {e}")
        raise DatabaseError(f"Ошибка получения списка кандидатов: {e}")


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
        raise DatabaseError(f"Ошибка установки времени: {e}")


async def select_candidate(event_id: str, user_id: int, selected: bool) -> bool:
    """Установить статус 'Выбран' через transition_application."""
    target = ApplicationStatus.ACCEPTED if selected else ApplicationStatus.REJECTED
    try:
        from services.candidate_service import transition_application
        return await transition_application(event_id, user_id, target)
    except Exception:
        # Fallback на старую логику если переход невозможен (для совместимости)
        db = get_db()
        db.table("event_candidates").update({"selected": selected}).eq("event_id", event_id).eq("user_id", user_id).execute()
        return True

async def get_voters(event_id: str) -> list:
    """Прослойка для обратной совместимости."""
    return await get_applicants(event_id)

async def get_selected_candidates(event_id: str) -> list:
    """Прослойка для обратной совместимости (только принятые)."""
    return await get_applicants(event_id, status=ApplicationStatus.ACCEPTED)

async def confirm_checkin(event_id: str, user_id: int) -> bool:
    """Подтвердить приход кандидата."""
    try:
        db = get_db()
        db.table("event_candidates").update({
            "is_checkin_confirmed": True
        }).eq("event_id", event_id).eq("user_id", user_id).execute()
        return True
    except Exception as e:
        logger.error(f"Error confirm_checkin {user_id}: {e}")
        return False



# ── Профили кандидатов ───────────────────────────────────────────────────────


# BUG-6 FIX: Removed duplicate `update_gender` function (old version).
# The canonical version is `update_candidate_gender` defined earlier.


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
        raise DatabaseError(f"Ошибка получения профиля: {e}")

async def update_candidate_full_name(user_id: int, full_name: str) -> bool:
    """Обновить ФИО кандидата."""
    try:
        db = get_db()
        db.table("candidates").update({"full_name": full_name}).eq("user_id", user_id).execute()
        return True
    except Exception as e:
        logger.error(f"Ошибка обновления ФИО для {user_id}: {e}")
        raise DatabaseError(f"Ошибка обновления ФИО: {e}")

async def get_company_applicants(company_id: str) -> list:
    """Получить всех кандидатов для всех мероприятий компании."""
    try:
        db = get_db()
        # Получаем все мероприятия компании
        events_res = db.table("events").select("event_id").eq("company_id", company_id).execute()
        event_ids = [e["event_id"] for e in events_res.data]
        
        if not event_ids:
            return []
            
        # Получаем всех кандидатов для этих мероприятий с данными профилей и мероприятий
        result = (
            db.table("event_candidates")
            .select("*, candidates(*), events(*)")
            .in_("event_id", event_ids)
            .execute()
        )
        return result.data
    except Exception as e:
        logger.error(f"Ошибка get_company_applicants: {e}")
        return []

async def update_candidate_role(user_id: int, role: str) -> bool:
    """Обновить роль кандидата."""
    try:
        db = get_db()
        db.table("candidates").update({"primary_role": role}).eq("user_id", user_id).execute()
        return True
    except Exception as e:
        logger.error(f"Ошибка обновления роли для {user_id}: {e}")
        return False


