import os
import requests
from google.oauth2.credentials import Credentials, _GOOGLE_OAUTH2_TOKEN_INFO_ENDPOINT
from googleapiclient.discovery import build
from dotenv import load_dotenv
from datetime import datetime, timedelta
from fastapi import HTTPException

load_dotenv()
MAIL_SUBJECT = os.getenv("MAIL_SUBJECT", "הגיפט קארד של Wolt הגיע ומחכה לשליחה")


class GmailClient:
    def __init__(self, token):
        """
        Initialize the Gmail client using the provided token.

        Args:
            token: Google OAuth access token

        Raises:
            HTTPException: If token validation fails
        """
        self.token = token
        self.user_info = self._validate_token(token)
        self.gmail_service = self._create_gmail_service(token)

    def _validate_token(self, token):
        """Validate Google access token and return user info."""
        try:
            tokeninfo_url = f"{_GOOGLE_OAUTH2_TOKEN_INFO_ENDPOINT}?access_token={token}"
            response = requests.get(tokeninfo_url)

            if response.status_code != 200:
                raise HTTPException(
                    status_code=401, detail="Invalid Google access token"
                )

            token_info = response.json()
            google_sub = token_info.get("sub")

            if not google_sub:
                raise HTTPException(
                    status_code=401, detail="Could not verify Google user identity"
                )

            return token_info

        except Exception as e:
            raise HTTPException(
                status_code=401, detail=f"Error validating Google token: {str(e)}"
            )

    def _create_gmail_service(self, access_token):
        """Create a Gmail API service using the access token."""
        creds = Credentials(token=access_token)
        return build("gmail", "v1", credentials=creds)

    def get_sub(self):
        """Get authenticated subject for the Gmail client"""
        if not self.user_info:
            raise ValueError("No authenticated user found")

        return self.user_info.get("sub")

    def get_attachments(self, msg_id, message_payload):
        """Get attachments from a message."""
        if not self.gmail_service:
            raise ValueError("Client not authenticated. Call authenticate() first.")

        attachments = []

        # If the message has parts (multipart message)
        if "parts" in message_payload:
            for part in message_payload["parts"]:
                # If this part is an attachment
                if (
                    "filename" in part
                    and part["filename"]
                    and "attachmentId" in part["body"]
                ):
                    attachment = {
                        "filename": part["filename"],
                        "mimeType": part["mimeType"],
                        "data": None,
                    }

                    # Get the attachment data
                    attachment_id = part["body"]["attachmentId"]
                    attachment_data = (
                        self.gmail_service.users()
                        .messages()
                        .attachments()
                        .get(userId="me", messageId=msg_id, id=attachment_id)
                        .execute()
                    )

                    # Store the attachment data as is (base64 encoded)
                    if "data" in attachment_data:
                        attachment["data"] = attachment_data["data"]

                    attachments.append(attachment)

                # Recursive check for nested parts (sometimes attachments are nested)
                if "parts" in part:
                    nested_attachments = self.get_attachments(msg_id, part)
                    attachments.extend(nested_attachments)

        return attachments

    def fetch_wolt_gift_card_emails(self, subject=MAIL_SUBJECT, days=30):
        """
        Fetch all Wolt Gift Card emails from Gmail within the specified days.
        Returns only the email metadata without attachments.
        """
        if not self.gmail_service:
            raise ValueError("Client not authenticated. Call authenticate() first.")

        # Calculate the date N days ago in the format YYYY/MM/DD
        days_ago = (datetime.now() - timedelta(days=days)).strftime("%Y/%m/%d")

        # Construct the search query with date filter
        search_query = f'from:info@wolt.com subject:"{subject}" after:{days_ago}'

        # Fetch messages matching the query
        results = (
            self.gmail_service.users()
            .messages()
            .list(userId="me", q=search_query, maxResults=100)
            .execute()
        )
        messages = results.get("messages", [])

        if not messages:
            return {
                "message": f"No Wolt Gift Card emails found in the last {days} days",
                "emails": [],
            }

        # Fetch basic details for each matching message
        emails = []

        for msg in messages:
            msg_id = msg["id"]
            message_detail = (
                self.gmail_service.users()
                .messages()
                .get(userId="me", id=msg_id, format="metadata")
                .execute()
            )

            # Add the message metadata
            emails.append({
                "message_id": msg_id,
                "message_detail": message_detail
            })

        return {"emails": emails}

    def fetch_email_attachments(self, message_id):
        """
        Fetch all attachments for a specific email message.
        
        Args:
            message_id: The ID of the Gmail message to fetch attachments from
            
        Returns:
            List of attachments with their data
        """
        if not self.gmail_service:
            raise ValueError("Client not authenticated. Call authenticate() first.")

        message_detail = (
            self.gmail_service.users()
            .messages()
            .get(userId="me", id=message_id, format="full")
            .execute()
        )

        payload = message_detail.get("payload", {})
        return self.get_attachments(message_id, payload)
