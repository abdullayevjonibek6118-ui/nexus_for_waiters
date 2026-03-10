import os
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

load_dotenv()
GOOGLE_CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "vivid-brand-488707-u6-9cc582df9bae.json")
SCOPES = ["https://www.googleapis.com/auth/drive"]

def test_drive():
    try:
        creds = Credentials.from_service_account_file(GOOGLE_CREDENTIALS_FILE, scopes=SCOPES)
        drive_service = build("drive", "v3", credentials=creds)
        file_metadata = {
            'name': 'Test Document',
            'mimeType': 'application/vnd.google-apps.document'
        }
        print("Testing Drive API File Creation...")
        file = drive_service.files().create(body=file_metadata, fields='id').execute()
        print(f"SUCCESS: Created file with ID {file.get('id')}")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == '__main__':
    test_drive()
