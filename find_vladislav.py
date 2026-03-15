import asyncio
from services import recruiter_service
from database import supabase

async def main():
    res = supabase.table("recruiters").select("*, companies(*)").execute()
    print("All Recruiters:")
    for rec in res.data:
        name = f"{rec.get('first_name', '')} {rec.get('last_name', '')}".strip()
        comp_name = rec["companies"]["name"] if rec.get("companies") else "No Company"
        chat_id = rec["companies"]["group_chat_id"] if rec.get("companies") else "N/A"
        print(f" - {name} (ID: {rec['user_id']}) | Company: {comp_name} | ChatID: {chat_id}")

    # Check candidates too, maybe he is registered as candidate or just started onboarding
    res = supabase.table("candidates").select("*").execute()
    print("\nAll Candidates (sample):")
    for cand in res.data[:20]:
        print(f" - {cand.get('first_name')} {cand.get('last_name')} (@{cand.get('telegram_username')}) | ID: {cand['user_id']}")

if __name__ == "__main__":
    asyncio.run(main())
