"""
Nexus AI — Custom Exceptions
"""

class NexusError(Exception):
    """Базовое исключение для проекта."""
    pass

class DatabaseError(NexusError):
    """Ошибка при работе с базой данных."""
    pass

class EventNotFoundError(NexusError):
    """Мероприятие не найдено."""
    pass

class AccessDeniedError(NexusError):
    """Ошибка доступа (изоляция данных)."""
    pass

class ValidationError(NexusError):
    """Ошибка валидации данных."""
    pass
