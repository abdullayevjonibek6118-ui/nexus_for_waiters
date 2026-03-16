
import asyncio
from database import get_db

async def check_schema():
    db = get_db()
    
    # Check one row from event_candidates with join
    print("Fetching one row from event_candidates with candidates join...")
    result = db.table("event_candidates").select("*, candidates(*)").limit(1).execute()
    if result.data:
        import json
        print(json.dumps(result.data[0], indent=2, ensure_ascii=False))
    else:
        print("event_candidates table is empty")
        
    # Also check if 'candidates' table has data
    print("\nFetching one row from candidates table...")
    result_c = db.table("candidates").select("*").limit(1).execute()
    if result_c.data:
        print(json.dumps(result_c.data[0], indent=2, ensure_ascii=False))
    else:
        print("candidates table is empty")

if __name__ == "__main__":
    asyncio.run(check_schema())
