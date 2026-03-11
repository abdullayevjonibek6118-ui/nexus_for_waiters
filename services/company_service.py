"""
Nexus AI — Company Service
Управление компаниями и подписками
"""
from datetime import datetime
from database import supabase

async def create_company(name: str, monthly_fee: float = 0, group_chat_id: int = None):
    """Создать новую компанию."""
    res = supabase.table("companies").insert({
        "name": name,
        "monthly_fee": monthly_fee,
        "group_chat_id": group_chat_id,
        "status": "active"
    }).execute()
    return res.data[0] if res.data else None

async def get_company(company_id: str):
    """Получить данные компании."""
    res = supabase.table("companies").select("*").eq("id", company_id).execute()
    return res.data[0] if res.data else None

async def list_companies():
    """Список всех компаний."""
    res = supabase.table("companies").select("*").order("created_at").execute()
    return res.data

async def update_subscription(company_id: str, until: datetime):
    """Продлить подписку."""
    res = supabase.table("companies").update({
        "subscription_until": until.isoformat(),
        "status": "active"
    }).eq("id", company_id).execute()
    return res.data[0] if res.data else None

async def check_subscription(company_id: str) -> bool:
    """Проверить, активна ли подписка."""
    company = await get_company(company_id)
    if not company:
        return False
    
    if company["status"] != "active":
        return False
        
    until = company.get("subscription_until")
    if not until:
        return False
        
    until_dt = datetime.fromisoformat(until.replace("Z", "+00:00"))
    return until_dt > datetime.now(until_dt.tzinfo)
