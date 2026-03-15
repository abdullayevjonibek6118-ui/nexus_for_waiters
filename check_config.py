import asyncio
from config import settings
from services import recruiter_service
from database import supabase

async def main():
    user_id = 785809306
    print(f"Checking config for user_id: {user_id}")
    
    # Check rec profile
    rec_profile = await recruiter_service.get_recruiter(user_id)
    print(f"Recruiter Profile: {rec_profile}")
    
    if rec_profile:
        group_chat_id = rec_profile["companies"].get("group_chat_id") if rec_profile.get("companies") else settings.group_chat_id
        print(f"Resolved group_chat_id from DB/Env: {group_chat_id}")
    else:
        print(f"No recruiter profile found. Default from .env: {settings.group_chat_id}")

    # Also list all companies and their chat IDs
    res = supabase.table("companies").select("*").execute()
    print("\nCompanies in DB:")
    for comp in res.data:
        print(f" - {comp['name']}: ID={comp['id']}, ChatID={comp['group_chat_id']}")

if __name__ == "__main__":
    asyncio.run(main())
