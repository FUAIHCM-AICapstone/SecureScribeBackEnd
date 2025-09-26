import re
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request

from app.core.config import settings
from app.schemas.common import ApiResponse
from app.schemas.google_calendar import (
    GoogleCalendarConnectResponse,
)
from app.services.google_calendar_service import GoogleCalendarService
from app.utils.auth import get_current_user

router = APIRouter(prefix=settings.API_V1_STR, tags=["Google Calendar"])


@router.get(
    "/auth/google/connect", response_model=ApiResponse[GoogleCalendarConnectResponse]
)
def connect_google_calendar(user_id: UUID = Depends(get_current_user)):
    """Initiate Google Calendar OAuth connection"""
    service = GoogleCalendarService()
    try:
        result = service.initiate_oauth_flow(user_id)
        return ApiResponse(success=True, message="OAuth flow initiated", data=result)
    except Exception as e:
        print(f"\033[91mError initiating Google Calendar OAuth: {e}\033[0m")
        raise HTTPException(status_code=500, detail="Failed to initiate OAuth flow")


@router.get("/auth/google/callback", response_model=ApiResponse[dict])
def google_calendar_callback(request: Request):
    """Handle Google Calendar OAuth callback"""

    # Get query params from the request
    params = request.query_params
    state = params.get("state")
    code = params.get("code")
    error = params.get("error")

    if error:
        print(f"\033[91mOAuth error received: {error}\033[0m")
        raise HTTPException(status_code=400, detail="OAuth error: " + error)

    if not code:
        print("\033[91mNo authorization code received\033[0m")
        raise HTTPException(status_code=400, detail="No authorization code received")

    # Try to extract UUID from the state string
    user_id = None
    if state:
        match = re.search(r"id=UUID\('([a-f0-9\-]+)'\)", state)
        if match:
            user_id = UUID(match.group(1))

    if not user_id:
        print("\033[91mNo user ID found in state parameter\033[0m")
        raise HTTPException(status_code=400, detail="Invalid state parameter")

    service = GoogleCalendarService()
    try:
        success = service.handle_oauth_callback(code, user_id)
        if success:
            return ApiResponse(
                success=True, message="Google Calendar connected successfully"
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to store refresh token")
    except Exception as e:
        print(f"\033[91mError in OAuth callback: {e}\033[0m")
        raise HTTPException(status_code=500, detail="OAuth callback failed")


@router.get("/calendar/events", response_model=ApiResponse[list])
def get_calendar_events(user_id: UUID = Depends(get_current_user)):
    """Get Google Calendar events for user"""
    service = GoogleCalendarService()
    try:
        events = service.fetch_events(user_id)
        return ApiResponse(
            success=True, message="Events retrieved successfully", data=events
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"\033[91mError fetching Google Calendar events: {e}\033[0m")
        raise HTTPException(
            status_code=500, detail="Failed to fetch events, please retry"
        )
