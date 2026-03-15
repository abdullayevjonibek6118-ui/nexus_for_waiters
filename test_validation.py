import asyncio
from database import supabase
from models.event import Event

async def check():
    print("Testing Pydantic validation on DB events...")
    res = supabase.table("events").select("*").execute()
    for row in res.data:
        try:
            ev = Event(**row)
            print(f"✅ Success: {ev.title} ({row['status']})")
        except Exception as e:
            print(f"❌ Failed: {row.get('title')} - Status in DB: '{row['status']}' - Error: {e}")

if __name__ == "__main__":
    asyncio.run(check())
