import asyncio
import logging
from database import supabase

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Mapping legacy/lowercase statuses to official EventStatus values
STATUS_MAPPING = {
    "draft": "Draft",
    "polling": "Poll_Published",
    "recruiting": "Recruiting",
    "confirmed": "Candidates_Confirmed",
    "cancelled": "Cancelled",
    "completed": "Completed"
}

async def migrate_statuses():
    logger.info("Starting event status migration...")
    
    # 1. Fetch all events
    res = supabase.table("events").select("event_id, title, status").execute()
    
    if not res.data:
        logger.info("No events found to migrate.")
        return

    updated_count = 0
    for row in res.data:
        old_status = row["status"]
        if old_status in STATUS_MAPPING:
            new_status = STATUS_MAPPING[old_status]
            logger.info(f"Updating '{row['title']}' ({row['event_id']}): {old_status} -> {new_status}")
            
            try:
                supabase.table("events").update({"status": new_status}).eq("event_id", row["event_id"]).execute()
                updated_count += 1
            except Exception as e:
                logger.error(f"Failed to update event {row['event_id']}: {e}")
        else:
            logger.debug(f"Skipping '{row['title']}' with status '{old_status}' (stet)")

    logger.info(f"Migration completed. Updated {updated_count} records.")

if __name__ == "__main__":
    asyncio.run(migrate_statuses())
