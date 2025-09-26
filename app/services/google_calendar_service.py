import uuid
from typing import Any, Dict, List

from fastapi import HTTPException

from app.schemas.google_calendar import GoogleCalendarConnectResponse
from app.utils.google_calendar import (
    create_oauth_flow,
    exchange_code_for_token,
    fetch_calendar_events,
    get_refresh_token,
    store_refresh_token,
)


class GoogleCalendarService:
    """Service for Google Calendar integration"""

    def initiate_oauth_flow(self, user_id: uuid.UUID) -> GoogleCalendarConnectResponse:
        """Create OAuth flow for Google Calendar connection"""
        flow = create_oauth_flow()
        auth_url, state = flow.authorization_url(
            access_type="offline", include_granted_scopes="true"
        )
        return GoogleCalendarConnectResponse(auth_url=auth_url, state=state)

    def handle_oauth_callback(self, code: str, user_id: uuid.UUID) -> bool:
        """Process OAuth callback and store refresh token"""
        try:
            print(f"\033[93m=== GOOGLE CALENDAR HANDLE OAUTH CALLBACK ===\ncode: {code}\nuser_id: {user_id}\033[0m")
            credentials = exchange_code_for_token(code)
            print(f"\033[93m[GoogleCalendarService] Exchanged code for credentials: {credentials}\033[0m")
            refresh_token_value = credentials.refresh_token
            print(f"\033[93m[GoogleCalendarService] Extracted refresh_token: {refresh_token_value}\033[0m")

            if not refresh_token_value:
                print(f"\033[91m[GoogleCalendarService] No refresh token received for user_id: {user_id}\033[0m")
                raise HTTPException(status_code=400, detail="No refresh token received")

            result = store_refresh_token(user_id, refresh_token_value)
            print(f"\033[93m[GoogleCalendarService] Stored refresh token for user_id: {user_id}, result: {result}\033[0m")
            return result
        except Exception as e:
            print(f"\033[91m[GoogleCalendarService] Exception in handle_oauth_callback: {e}\033[0m")
            raise HTTPException(status_code=500, detail="OAuth failed") from e

    def fetch_events(self, user_id: uuid.UUID) -> List[Dict[str, Any]]:
        """Get calendar events for user"""
        refresh_token_value = get_refresh_token(user_id)
        if not refresh_token_value:
            raise HTTPException(status_code=400, detail="Google Calendar not connected")

        return fetch_calendar_events(refresh_token_value)
