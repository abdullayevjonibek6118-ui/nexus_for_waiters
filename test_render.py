import asyncio
from services.candidate_service import get_candidate_profile, get_event_candidate

async def check():
    event_id = "ae8d90ed-37c5-4329-b426-b08b0fb774ff"
    uids = [1058294904, 277768350, 2014694401, 1480696492, 472941641]
    
    for uid in uids:
        print(f"Testing uid: {uid}")
        cand = await get_candidate_profile(uid)
        if not cand:
            print("Cand is none")
            continue
            
        ec = await get_event_candidate(event_id, uid)
        
        fullname = cand.full_name or cand.first_name
        gender_icon = "👨" if cand.gender == "Male" else "👩" if cand.gender == "Female" else "🧑"
        
        text = (
            f"🙋‍♂️ <b>Карточка кандидата</b>\n"
            f"📦 X из X\n"
            "━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👤 <b>ФИО:</b> {fullname}\n"
            f"{gender_icon} <b>Пол:</b> {'Мужской' if cand.gender == 'Male' else 'Женский' if cand.gender == 'Female' else 'Не указан'}\n"
            f"🎭 <b>Роль:</b> {cand.primary_role or 'Не указана'}\n"
            f"⏰ <b>Удобное время:</b> {ec.get('arrival_time', 'Не указано')}\n"
            f"📱 <b>Телефон:</b> <code>{cand.phone_number or 'Не указан'}</code>\n\n"
            "✨ <i>Примите решение по кандидату:</i>"
        )
        print(text)
        print("-" * 50)

if __name__ == "__main__":
    asyncio.run(check())
