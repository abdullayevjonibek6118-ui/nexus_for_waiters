import asyncio
from database import supabase

async def main():
    res = supabase.table("events").select("*, companies(*)").ilike("title", "%Алякард%").execute()
    print("Found Events matching 'Алякард':")
    for ev in res.data:
        print(f" - {ev['title']} (ID: {ev['event_id']})")
        print(f"   Created by: {ev['created_by']}")
        print(f"   Company: {ev['companies']['name'] if ev.get('companies') else 'None'}")
        print(f"   Company ChatID: {ev['companies']['group_chat_id'] if ev.get('companies') else 'N/A'}")
        print(f"   Status: {ev['status']}")
        print("-" * 20)

if __name__ == "__main__":
    asyncio.run(main())
