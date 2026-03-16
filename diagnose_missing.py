
import asyncio
from database import get_db

async def debug_candidates():
    db = get_db()
    # Возьмем последние 10 записей из event_candidates
    result = db.table("event_candidates").select("event_id, user_id, application_status, role, selected, confirmed").limit(10).execute()
    print("--- event_candidates sample ---")
    for row in result.data:
        print(row)
        
    # Проверим, есть ли записи с NULL role или NULL application_status
    null_role = db.table("event_candidates").select("count").is_("role", "null").execute()
    null_status = db.table("event_candidates").select("count").is_("application_status", "null").execute()
    print(f"\nRecords with NULL role: {null_role.data}")
    print(f"Records with NULL application_status: {null_status.data}")

if __name__ == "__main__":
    asyncio.run(debug_candidates())
