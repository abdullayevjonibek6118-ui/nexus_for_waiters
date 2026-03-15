"""
Nexus AI — Google Sheets Service
Создание и заполнение таблиц для мероприятий
"""
import logging
from typing import Optional, List
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from config import settings

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def _create_spreadsheet_sync(event_title: str, event_date: str, event_location: str, candidates: List[dict]):
    """Синхронная логика создания таблицы для asyncio.to_thread."""
    sheets_svc, drive_svc = _get_service()
    sheet_name = f"{event_date} - {event_location} - {event_title}"

    # Создать новую таблицу
    spreadsheet_body = {
        "properties": {"title": sheet_name},
        "sheets": [{"properties": {"title": "Кандидаты"}}],
    }
    spreadsheet = sheets_svc.spreadsheets().create(body=spreadsheet_body).execute()
    spreadsheet_id = spreadsheet["spreadsheetId"]
    sheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"

    # Заголовки
    headers = [["ФИО", "Пол", "Номер телефона", "Время прихода", "Время ухода", "Подтверждён"]]

    rows = []
    for c in candidates:
        profile = c.get("candidates", {}) or {}
        full_name = profile.get("full_name") or f"{profile.get('first_name', '')} {profile.get('last_name', '')}".strip()
        gender_raw = profile.get("gender", "—")
        gender = "Мужской" if gender_raw == "Male" else "Женский" if gender_raw == "Female" else gender_raw
        phone = profile.get("phone_number", "—")
        arrival = c.get("arrival_time", "—")
        departure = c.get("departure_time", "—")
        confirmed = "✅" if c.get("confirmed") else "❌"
        rows.append([full_name, gender, phone, arrival, departure, confirmed])

    values = headers + rows

    sheets_svc.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range="Кандидаты!A1",
        valueInputOption="USER_ENTERED",
        body={"values": values},
    ).execute()

    requests = [
        {
            "repeatCell": {
                "range": {"sheetId": 0, "startRowIndex": 0, "endRowIndex": 1},
                "cell": {
                    "userEnteredFormat": {
                        "textFormat": {"bold": True},
                        "backgroundColor": {"red": 0.2, "green": 0.6, "blue": 1.0},
                    }
                },
                "fields": "userEnteredFormat(textFormat,backgroundColor)",
            }
        },
        {
            "autoResizeDimensions": {
                "dimensions": {"sheetId": 0, "dimension": "COLUMNS", "startIndex": 0, "endIndex": 5}
            }
        },
    ]
    sheets_svc.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests}).execute()

    # drive_svc.permissions().create(fileId=spreadsheet_id, body={"type": "anyone", "role": "reader"}).execute()
    
    return sheet_url

async def create_event_sheet(
    event_title: str,
    event_date: str,
    event_location: str,
    candidates: List[dict],
) -> Optional[str]:
    """Асинхронный обёртка над созданием Google Sheet."""
    try:
        import asyncio
        url = await asyncio.to_thread(
            _create_spreadsheet_sync,
            event_title, event_date, event_location, candidates
        )
        logger.info(f"Google Sheet создана: {url}")
        return url
    except Exception as e:
        logger.error(f"Ошибка создания Google Sheet: {e}")
        return None
