"""
Nexus AI — Event Service
Управление мероприятиями в Supabase
"""
import uuid
import logging
from typing import Optional, List
from database import get_db
from models.event import Event, EventStatus

logger = logging.getLogger(__name__)


async def create_event(event: Event) -> Optional[Event]:
    """Создать новое мероприятие в Supabase."""
    try:
        db = get_db()
        event_id = str(uuid.uuid4())
        data = {
            "event_id": event_id,
            "company_id": event.company_id,
            "title": event.title,
            "date": event.date,
            "location": event.location,
            "max_candidates": event.max_candidates,
            "required_roles": event.required_roles,
            "arrival_times": event.arrival_times,
            "required_men": event.required_men,
            "required_women": event.required_women,
            "status": event.status.value,
            "created_by": event.created_by,
        }
        result = db.table("events").insert(data).execute()
        if result.data:
            event.event_id = event_id
            return event
        return None
    except Exception as e:
        logger.error(f"Ошибка создания мероприятия: {e}")
        return None


async def get_event(event_id: str) -> Optional[Event]:
    """Получить мероприятие по ID."""
    try:
        db = get_db()
        result = db.table("events").select("*").eq("event_id", event_id).single().execute()
        if result.data:
            return Event(**result.data)
        return None
    except Exception as e:
        logger.error(f"Ошибка получения мероприятия {event_id}: {e}")
        return None


async def get_active_events(company_id: Optional[str] = None) -> List[Event]:
    """Получить список незакрытых мероприятий (опционально по компании)."""
    try:
        db = get_db()
        query = (
            db.table("events")
            .select("*")
            .neq("status", EventStatus.CLOSED.value)
            .neq("status", EventStatus.COMPLETED.value)
        )
        
        if company_id:
            query = query.eq("company_id", company_id)
            
        result = query.order("date").execute()
        
        events = []
        for row in (result.data or []):
            try:
                events.append(Event(**row))
            except Exception as parse_err:
                logger.warning(f"Skipping malformed event {row.get('event_id', 'unknown')}: {parse_err}")
                
        return events
    except Exception as e:
        logger.error(f"Ошибка получения мероприятий: {e}")
        return []


async def update_event_status(event_id: str, status: EventStatus) -> bool:
    """Обновить статус мероприятия."""
    try:
        db = get_db()
        db.table("events").update({"status": status.value}).eq("event_id", event_id).execute()
        return True
    except Exception as e:
        logger.error(f"Ошибка обновления статуса мероприятия {event_id}: {e}")
        return False


async def save_poll_id(event_id: str, poll_id: str) -> bool:
    """Сохранить poll_id и установить статус Poll_Published."""
    try:
        db = get_db()
        db.table("events").update({
            "poll_id": poll_id,
            "status": EventStatus.POLL_PUBLISHED.value
        }).eq("event_id", event_id).execute()
        return True
    except Exception as e:
        logger.error(f"Ошибка сохранения poll_id: {e}")
        return False


async def save_sheet_url(event_id: str, sheet_url: str) -> bool:
    """Сохранить URL Google Sheet."""
    try:
        db = get_db()
        db.table("events").update({
            "sheet_url": sheet_url,
            "status": EventStatus.SHEET_GENERATED.value
        }).eq("event_id", event_id).execute()
        return True
    except Exception as e:
        logger.error(f"Ошибка сохранения sheet_url: {e}")
        return False


async def get_event_by_poll_id(poll_id: str) -> Optional[Event]:
    """Найти мероприятие по poll_id."""
    try:
        db = get_db()
        result = db.table("events").select("*").eq("poll_id", poll_id).single().execute()
        if result.data:
            return Event(**result.data)
        return None
    except Exception as e:
        logger.error(f"Ошибка поиска мероприятия по poll_id {poll_id}: {e}")
        return None
