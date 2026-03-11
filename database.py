"""
Nexus AI Bot — Supabase Client
Singleton-клиент для работы с базой данных Supabase
"""
from supabase import create_client, Client
from config import settings

_client: Client | None = None


def get_db() -> Client:
    """Возвращает singleton-клиент Supabase."""
    global _client
    if _client is None:
        _client = create_client(settings.supabase_url, settings.supabase_key)
    return _client


supabase = get_db()
