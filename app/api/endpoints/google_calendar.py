from fastapi import APIRouter, Depends, HTTPException, Request

from app.core.config import settings
from app.models.user import User
from app.schemas.common import ApiResponse
from app.services.google_calendar_service import GoogleCalendarService
from app.utils.auth import get_current_user

router = APIRouter(prefix=settings.API_V1_STR, tags=["Google Calendar"])


@router.get(
    "/auth/google/connect", response_model=ApiResponse
)
def connect_google_calendar(current_user: User = Depends(get_current_user)):
    """Initiate Google Calendar OAuth connection"""
    service = GoogleCalendarService()
    try:
        result = service.initiate_oauth_flow(current_user.id)
        result_response = {
            "auth_url": result.auth_url,
            "state": result.state,
        }
        return ApiResponse(success=True, message="OAuth flow initiated", data=result_response)
    except Exception as e:
        print(f"\033[91mError initiating Google Calendar OAuth: {e}\033[0m")
        raise HTTPException(status_code=500, detail="Failed to initiate OAuth flow")


@router.get("/auth/google/callback", response_model=ApiResponse)
def google_calendar_callback(request: Request):
    """Handle Google Calendar OAuth callback"""

    # Get query params from the request
    params = request.query_params
    state = params.get("state")
    code = params.get("code")
    error = params.get("error")
    print(f"\033[91mOAuth error received: {error}\033[0m")
    print(f"\033[91mOAuth code received: {code}\033[0m")
    print(f"\033[91mOAuth state received: {state}\033[0m")

    if error:
        print(f"\033[91mOAuth error received: {error}\033[0m")
        raise HTTPException(status_code=400, detail="OAuth error: " + error)

    if not code:
        print("\033[91mNo authorization code received\033[0m")
        raise HTTPException(status_code=400, detail="No authorization code received")

    if not state:
        print("\033[91mNo state parameter received\033[0m")
        raise HTTPException(status_code=400, detail="No state parameter received")

    # Get user_id from Redis using the state as key
    from app.utils.google_calendar import get_user_id_from_state
    user_id = get_user_id_from_state(state)

    if not user_id:
        print(f"\033[91mNo user ID found for state: {state}\033[0m")
        raise HTTPException(status_code=400, detail="Invalid or expired state parameter")

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


@router.get("/calendar/events", response_model=ApiResponse)
def get_calendar_events(current_user: User = Depends(get_current_user)):
    """Get Google Calendar events for user"""
    service = GoogleCalendarService()
    try:
        events = service.fetch_events(current_user.id)
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
