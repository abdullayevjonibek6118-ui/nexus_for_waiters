
import asyncio
from database import get_db
from services import candidate_service

async def debug_live_applicants():
    db = get_db()
    
    # Find event_id that definitely has candidates
    print("Searching for an event with candidates...")
    ec_result = db.table("event_candidates").select("event_id").limit(1).execute()
    if not ec_result.data:
        print("No event_candidates found at all!")
        return
        
    event_id = ec_result.data[0]["event_id"]
    print(f"Found event with candidates: {event_id}")
    
    applicants = await candidate_service.get_applicants(event_id)
    if not applicants:
        print("get_applicants returned empty list for this event!")
        return
    
    import json
    print("\nDEBUG: First applicant raw data:")
    print(json.dumps(applicants[0], indent=2, ensure_ascii=False))
    
    cand_profile = applicants[0].get("candidates")
    print(f"\nType of 'candidates' field: {type(cand_profile)}")

if __name__ == "__main__":
    asyncio.run(debug_live_applicants())
