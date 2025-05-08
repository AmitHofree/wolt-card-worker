import base64
import tempfile
import os
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from parse_pdf import extract_gift_card_details
from gmail_client import GmailClient
from supabase_client import SupabaseClient

load_dotenv()

origins = (
    [
        "http://localhost",
        "http://localhost:8080",
        "https://wch.apps.lizardbaby.com",
    ]
    if os.getenv("ENV") == "development"
    else ["https://wch.apps.lizardbaby.com"]
)

app = FastAPI(title="Wolt Gift Card API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def extract_codes_from_attachments(attachments):
    """
    Extract gift card codes from attachments.
    Returns a list of codes found with their values.

    This is a cross-functional utility that processes PDF attachments
    to extract gift card codes and values.
    """
    codes_with_values = []
    print(f"Processing {len(attachments)} attachments")

    for i, attachment in enumerate(attachments):
        print(f"Attachment {i+1}: {attachment['filename']} ({attachment['mimeType']})")

        is_pdf = attachment["mimeType"] == "application/pdf" or (
            attachment["mimeType"] == "application/octet-stream"
            and attachment["filename"].lower().endswith(".pdf")
        )

        if is_pdf and attachment["data"]:
            print(f"Processing PDF: {attachment['filename']}")
            # Create a temporary file to save the PDF
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
                pdf_path = temp_file.name
                # Decode base64 data and write to the file
                pdf_data = base64.urlsafe_b64decode(attachment["data"])
                temp_file.write(pdf_data)
                print(f"Saved PDF to temporary file: {pdf_path}")

                try:
                    # Extract code and value from the PDF using parse_pdf functions
                    code, value = extract_gift_card_details(pdf_path)
                    print(f"Extracted code: {code}, value: {value}")

                    if code:
                        codes_with_values.append({"code": code, "value": value})
                    else:
                        print("No code found in this PDF")
                except Exception as e:
                    print(f"Error extracting code from PDF: {str(e)}")

        else:
            print(f"Skipping non-PDF or empty attachment: {attachment['filename']}")

    print(f"Total codes found: {len(codes_with_values)}")
    return codes_with_values


@app.get("/")
async def root():
    """Root endpoint for health checks."""
    return {"status": "ok", "message": "Wolt Gift Card API is running"}


@app.get("/fetch-gift-cards")
async def fetch_gift_cards(
    authorization: str = Header(...),
    google_token: str = Header(..., alias="X-Google-Token"),
):
    """
    Fetch Wolt gift cards from Gmail and save them to Supabase.
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=400, detail="Invalid Authorization header")

    jwt_token = authorization.removeprefix("Bearer ").strip()
    supabase_client = SupabaseClient(jwt_token)
    gmail_client = GmailClient(google_token)

    supabase_sub = supabase_client.get_sub()
    gmail_sub = gmail_client.get_sub()

    if not supabase_sub == gmail_sub:
        return HTTPException(
            status_code=401,
            detail="Subjects for Supabase and Gmail don't match, stopping.",
        )

    gmail_result = gmail_client.fetch_wolt_gift_card_emails()
    if "message" in gmail_result:
        return {"total_codes": 0, "codes_saved": 0}

    all_codes_with_values = []
    processed_emails = []

    for email in gmail_result["emails"]:
        msg_id = email["message_id"]       
        if supabase_client.is_msg_id_cached(msg_id):
            print(f"Message ID {msg_id} already processed, skipping.")
            continue

        attachments = gmail_client.fetch_email_attachments(msg_id)
        codes_with_values = extract_codes_from_attachments(attachments)
        all_codes_with_values.extend(codes_with_values)
        processed_emails.append(
            {
                "message_id": msg_id,
                "codes": [item["code"] for item in codes_with_values],
            }
        )
        supabase_client.cache_msg_id(msg_id)

    saved_count = supabase_client.save_gift_card_codes(all_codes_with_values)
    distinct_codes = list(set(item["code"] for item in all_codes_with_values))

    return {"total_codes": len(distinct_codes), "codes_saved": saved_count}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
