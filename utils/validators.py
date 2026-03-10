"""
Nexus AI — Утилиты: Валидаторы входных данных
"""
import re
from datetime import datetime


def validate_time_format(time_str: str) -> bool:
    """Проверить формат времени HH:MM (24h)."""
    pattern = r"^([01]\d|2[0-3]):([0-5]\d)$"
    return bool(re.match(pattern, time_str.strip()))


def validate_date_format(date_str: str) -> bool:
    """Проверить формат даты DD.MM.YYYY."""
    try:
        datetime.strptime(date_str.strip(), "%d.%m.%Y")
        return True
    except ValueError:
        return False


def validate_max_candidates(value: str) -> tuple[bool, int]:
    """Проверить, что лимит кандидатов — целое число от 1 до 100."""
    try:
        n = int(value.strip())
        return (1 <= n <= 100), n
    except ValueError:
        return False, 0
