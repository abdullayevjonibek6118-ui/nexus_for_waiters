import asyncio
from services.candidate_service import get_voters
from services.event_service import get_event

async def check():
    event_id = "ae8d90ed-37c5-4329-b426-b08b0fb774ff"
    event = await get_event(event_id)
    print(f"Event: {event.title}")
    
    voters = await get_voters(event_id)
    print(f"Returned {len(voters)} voters initially via get_voters().")
    for v in voters:
        # Check if the joined candidates field is loaded correctly
        profile = v.get("candidates")
        print(f"Voter user_id: {v.get('user_id')} - Profile: {profile}")
        
if __name__ == "__main__":
    asyncio.run(check())
