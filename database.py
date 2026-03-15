import logging
from supabase import create_client, Client
from config import settings

logger = logging.getLogger(__name__)

_client: Client | None = None

def get_db() -> Client:
    """
    Возвращает singleton-клиент Supabase.
    Примечание: Supabase использует PostgREST (HTTP), поэтому традиционный пул соединений
    на стороне клиента не требуется, но мы обеспечиваем стабильный singleton.
    """
    global _client
    if _client is None:
        try:
            _client = create_client(settings.supabase_url, settings.supabase_key)
            logger.info("✅ Успешное подключение к Supabase")
        except Exception as e:
            logger.error(f"❌ Критическая ошибка подключения к Supabase: {e}")
            raise
    return _client

# По умолчанию инициализируем клиент лениво через прокси или просто вызываем при первом использовании.
# Для обратной совместимости оставляем глобальную переменную supabase.
supabase = get_db()
