import asyncio
from database import supabase

async def main():
    target_chat_id = -1002475882792
    company_name = "Cash 2.0"
    
    print(f"Updating group_chat_id for company '{company_name}' to {target_chat_id} (user requested)...")
    
    res = supabase.table("companies").update({"group_chat_id": target_chat_id}).eq("name", company_name).execute()
    
    if res.data:
        print(f"✅ Successfully updated {len(res.data)} company record(s).")
        for comp in res.data:
            print(f" - Company: {comp['name']} (ID: {comp['id']}) | New ChatID: {comp['group_chat_id']}")
    else:
        print(f"❌ Failed to update company '{company_name}'.")

if __name__ == "__main__":
    asyncio.run(main())
