from fastapi import FastAPI, Header, HTTPException
from dotenv import load_dotenv
from supabase import create_client
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import os

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

app = FastAPI()
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def get_gmail_service(access_token: str):
    """Create a Gmail API service using the access token."""
    creds = Credentials(token=access_token)
    return build("gmail", "v1", credentials=creds)


def fetch_latest_email_gmail(creds: Credentials):
    """Fetch the most recent email using the Gmail API."""
    service = build("gmail", "v1", credentials=creds)

    # Fetch the latest message ID
    results = service.users().messages().list(userId='me', maxResults=1).execute()
    messages = results.get("messages", [])
    if not messages:
        return {"message": "No emails found"}

    msg_id = messages[0]["id"]
    message = service.users().messages().get(userId='me', id=msg_id, format='full').execute()
    return message


@app.get("/latest-email")
async def get_latest_email(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=400, detail="Invalid Authorization header")

    jwt_token = authorization.removeprefix("Bearer ").strip()

    # Step 1: Validate JWT and fetch user
    user_response = supabase.auth.get_user(jwt_token)
    if not user_response.user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = user_response.user
    google_token = user.user_metadata.get("provider_token")

    if not google_token:
        raise HTTPException(status_code=400, detail="Google access token not found")

    # Step 2: Create Gmail service and fetch email
    creds = Credentials(token=google_token)
    email_data = fetch_latest_email_gmail(creds)

    return email_data
