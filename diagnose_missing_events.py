import asyncio
from database import supabase

async def diagnose():
    user_id = 6369037305
    print(f"--- Diagnosing User {user_id} ---")
    
    # 1. Check recruiter profile
    rec = supabase.table("recruiters").select("*, companies(*)").eq("user_id", user_id).execute()
    if not rec.data:
        print("Recruiter profile NOT FOUND.")
    else:
        profile = rec.data[0]
        print(f"Recruiter found: {profile.get('first_name')} {profile.get('last_name')}")
        print(f"Company: {profile.get('companies', {}).get('name')} (ID: {profile.get('company_id')})")
        print(f"Is Active: {profile.get('is_active')}")
        
    # 2. Find events created by this user
    events_created = supabase.table("events").select("*").eq("created_by", user_id).execute()
    print(f"\nEvents created by this user ({len(events_created.data)}):")
    for ev in events_created.data:
        print(f"- {ev['title']} | ID: {ev['event_id']} | Status: {ev['status']} | Company: {ev['company_id']}")
        
    # 3. Find ALL Алякард events
    print("\nAll 'Алякард' events in DB:")
    all_alyakard = supabase.table("events").select("*").ilike("title", "%Алякард%").execute()
    for ev in all_alyakard.data:
        print(f"- {ev['title']} | ID: {ev['event_id']} | Status: {ev['status']} | Company: {ev['company_id']} | CreatedBy: {ev['created_by']}")

if __name__ == "__main__":
    asyncio.run(diagnose())
