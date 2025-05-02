import os
from dotenv import load_dotenv
from supabase import create_client
from fastapi import HTTPException

load_dotenv()


class SupabaseClient:
    def __init__(self, token, url=None, key=None):
        """
        Initialize the Supabase client using the provided token.

        Args:
            token:  Supabase user access token
            url:    Supabase URL (if None, will look for SUPABASE_URL environment variable)
            key:    Supabase API key (if None, will look for SUPABASE_KEY environment variable)

        Raises:
            HTTPException:  If token validation fails
        """
        self.url = url or os.getenv("SUPABASE_URL")
        self.key = key or os.getenv("SUPABASE_KEY")

        if not self.url or not self.key:
            raise ValueError(
                "Supabase URL and key are required. Please provide them as arguments or set environment variables."
            )

        self.client = create_client(self.url, self.key)
        self.user = self._validate_token(token)

    def _validate_token(self, token):
        """
        Validate Supabase JWT token and return the user.
        Raises HTTPException if token is invalid.
        """
        try:
            user_response = self.client.auth.get_user(token)
            if not user_response.user:
                raise HTTPException(
                    status_code=401, detail="Invalid or expired Supabase token"
                )

            return user_response.user
        except Exception as e:
            raise HTTPException(
                status_code=401, detail=f"Error validating Supabase token: {str(e)}"
            )

    def get_sub(self):
        """Get authenticated subject for the Supabase client"""
        if not self.user:
            raise ValueError("No authenticated user found")

        return self.user.user_metadata['sub']

    def save_gift_card_codes(self, codes_with_values):
        """
        Save gift card codes to Supabase.
        Skip codes that already exist in the database.
        Returns the count of newly saved codes.
        """
        saved_count = 0

        for item in codes_with_values:
            code = item["code"]
            value = item["value"]

            # Check if code already exists in database
            existing = (
                self.client.table("wolt_gift_cards")
                .select("code")
                .eq("code", code)
                .execute()
            )

            if len(existing.data) == 0:
                # Code doesn't exist, insert it
                insert_data = {"code": code, "value": value, "user_id": self.user.id}

                self.client.table("wolt_gift_cards").insert(insert_data).execute()
                saved_count += 1
                print(f"Saved code {code} with value {value} to database")
            else:
                print(f"Code {code} already exists in database, skipping")

        return saved_count

    def get_user_gift_cards(self):
        """
        Get all gift cards for the authenticated user
        """
        query = (
            self.client.table("wolt_gift_cards").select("*").eq("user_id", self.user.id)
        )
        result = query.execute()
        return result.data
