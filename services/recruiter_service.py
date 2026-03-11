"""
Nexus AI — Recruiter Service
Управление рекрутерами
"""
from database import supabase

async def add_recruiter(user_id: int, company_id: str, first_name: str = None, last_name: str = None):
    """Добавить рекрутера в компанию."""
    res = supabase.table("recruiters").upsert({
        "user_id": user_id,
        "company_id": company_id,
        "first_name": first_name,
        "last_name": last_name,
        "is_active": True
    }).execute()
    return res.data[0] if res.data else None

async def get_recruiter(user_id: int):
    """Получить данные рекрутера и его компании."""
    res = supabase.table("recruiters").select("*, companies(*)").eq("user_id", user_id).execute()
    return res.data[0] if res.data else None

async def is_recruiter(user_id: int) -> bool:
    """Проверить, является ли пользователь рекрутером."""
    rec = await get_recruiter(user_id)
    return rec is not None and rec.get("is_active", False)

async def list_company_recruiters(company_id: str):
    """Список рекрутеров компании."""
    res = supabase.table("recruiters").select("*").eq("company_id", company_id).execute()
    return res.data
