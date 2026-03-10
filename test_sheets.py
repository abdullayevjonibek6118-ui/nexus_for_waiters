import os
import sys
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

load_dotenv()

# Simulate config settings
GOOGLE_CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "vivid-brand-488707-u6-9cc582df9bae.json")
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

def test_google_sheets():
    print(f"Checking credentials file: {GOOGLE_CREDENTIALS_FILE}")
    if not os.path.exists(GOOGLE_CREDENTIALS_FILE):
        print("❌ Error: Credentials file not found!")
        return

    try:
        creds = Credentials.from_service_account_file(
            GOOGLE_CREDENTIALS_FILE,
            scopes=SCOPES,
        )
        service = build("sheets", "v4", credentials=creds)
        drive_service = build("drive", "v3", credentials=creds)
        
        # Try to create a small test sheet
        body = {
            'properties': {'title': 'Nexus AI Test Sheet'}
        }
        print("Creating test spreadsheet...")
        spreadsheet = service.spreadsheets().create(body=body, fields='spreadsheetId').execute()
        spreadsheet_id = spreadsheet.get('spreadsheetId')
        print(f"✅ Success! Created spreadsheet with ID: {spreadsheet_id}")
        
        # Share it
        print("Sharing spreadsheet...")
        drive_service.permissions().create(
            fileId=spreadsheet_id,
            body={"type": "anyone", "role": "reader"},
        ).execute()
        print(f"✅ Spreadsheet is now public. URL: https://docs.google.com/spreadsheets/d/{spreadsheet_id}")
        
        # Delete it (optional, but good for cleanup)
        # drive_service.files().delete(fileId=spreadsheet_id).execute()
        # print("Cleanup: Deleted test spreadsheet.")
        
    except Exception as e:
        print(f"❌ API Test Failed: {e}")

if __name__ == "__main__":
    test_google_sheets()
