"""
Nexus AI Bot — Configuration
Загрузка настроек из .env файла через Pydantic Settings
"""
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Telegram
    bot_token: str
    super_admin_id: int               # Telegram ID владельца платформы
    admin_user_ids: str = ""          # строка вида "111,222,333" (устаревает, но оставим для совместимости)
    group_chat_id: int = 0

    # Supabase
    supabase_url: str
    supabase_key: str

    # Google Sheets
    google_credentials_file: str = "credentials/google_service_account.json"
    google_service_account_email: str = ""

    # Scheduler
    timezone: str = "Asia/Tashkent"

    # Logging
    log_level: str = "INFO"

    @property
    def admin_ids(self) -> List[int]:
        """Список Telegram user_id администраторов."""
        if not self.admin_user_ids:
            return []
        return [int(uid.strip()) for uid in self.admin_user_ids.split(",") if uid.strip()]


# Singleton настроек
settings = Settings()
