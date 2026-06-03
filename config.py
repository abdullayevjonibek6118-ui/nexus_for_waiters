"""
Nexus AI Bot — Configuration
Загрузка настроек из .env файла через Pydantic Settings
"""
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import ValidationError, field_validator


PROJECT_ROOT = Path(__file__).resolve().parent
ENV_FILE = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
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

    @field_validator("admin_user_ids")
    @classmethod
    def validate_admin_user_ids(cls, value: str) -> str:
        """Validate comma-separated Telegram user IDs at startup."""
        if not value:
            return ""
        invalid = [uid.strip() for uid in value.split(",") if uid.strip() and not uid.strip().isdigit()]
        if invalid:
            raise ValueError(f"ADMIN_USER_IDS contains non-numeric values: {', '.join(invalid)}")
        return value

    @property
    def admin_ids(self) -> List[int]:
        """Список Telegram user_id администраторов."""
        if not self.admin_user_ids:
            return []
        return [int(uid.strip()) for uid in self.admin_user_ids.split(",") if uid.strip()]


# Singleton настроек
try:
    settings = Settings()
except ValidationError as exc:
    missing_fields = [
        str(error["loc"][0]).upper()
        for error in exc.errors()
        if error.get("type") == "missing" and error.get("loc")
    ]
    missing_text = ", ".join(missing_fields) or "required environment variables"
    raise RuntimeError(
        "Missing required environment variables: "
        f"{missing_text}. "
        "Set them in your hosting provider secrets/environment settings "
        "or create a local .env file from .env.example."
    ) from exc
