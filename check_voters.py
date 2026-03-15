import asyncio
import os
from database import get_db

async def check():
    db = get_db()
    
    # 1. Get the latest event for user 785809306 (or just the latest event)
    # The event title is "Алякард" or we can get it by recruiter 6369037305 or user 785809306
    # Let's just find "Алякард"
    print("Fetching 'Алякард' events...")
    events = db.table("events").select("*").ilike("title", "%Алякард%").order("created_at", desc=True).execute()
    
    if not events.data:
        print("No event found.")
        return
        
    event = events.data[0]
    event_id = event["event_id"]
    print(f"Found event: {event['title']} ({event_id})")
    print(f"Status: {event['status']}")
    
    # Check candidates
    cands = db.table("event_candidates").select("*").eq("event_id", event_id).execute()
    print(f"Found {len(cands.data)} candidates in event_candidates:")
    for c in cands.data:
        print(c)

if __name__ == "__main__":
    asyncio.run(check())
