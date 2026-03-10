"""
Nexus AI — Audit Service
Запись и чтение аудит-логов из Supabase (таблица event_logs)
"""
import uuid
import logging
from datetime import datetime
from typing import List, Optional
from database import get_db

logger = logging.getLogger(__name__)


async def log_action(
    event_id: str,
    action: str,
    performed_by: int,
    details: Optional[dict] = None,
) -> bool:
    """Записать действие в аудит-лог."""
    try:
        db = get_db()
        db.table("event_logs").insert({
            "log_id": str(uuid.uuid4()),
            "event_id": event_id,
            "action": action,
            "performed_by": performed_by,
            "timestamp": datetime.utcnow().isoformat(),
            "details": details or {},
        }).execute()
        return True
    except Exception as e:
        logger.error(f"Ошибка записи аудит-лога: {e}")
        return False


async def get_event_logs(event_id: str, limit: int = 20) -> List[dict]:
    """Получить последние N записей аудит-лога для мероприятия."""
    try:
        db = get_db()
        result = (
            db.table("event_logs")
            .select("*")
            .eq("event_id", event_id)
            .order("timestamp", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data or []
    except Exception as e:
        logger.error(f"Ошибка получения аудит-логов: {e}")
        return []
