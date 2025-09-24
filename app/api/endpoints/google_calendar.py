from fastapi import APIRouter, HTTPException, Depends
from uuid import UUID
from app.services.google_calendar_service import GoogleCalendarService
from app.utils.auth import get_current_user
from typing import Dict, List, Any

router = APIRouter()

@router.get("/auth/google/connect")
def connect_google_calendar(user_id: UUID = Depends(get_current_user)):
    service = GoogleCalendarService()
    try:
        result = service.initiate_oauth_flow(user_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to initiate OAuth flow")

@router.get("/auth/google/callback")
def google_calendar_callback(code: str, user_id: UUID = Depends(get_current_user)):
    service = GoogleCalendarService()
    if service.handle_oauth_callback(code, user_id):
        return {"message": "Google Calendar connected successfully"}
    else:
        raise HTTPException(status_code=400, detail="Connection failed, please retry")

@router.get("/calendar/events")
def get_calendar_events(user_id: UUID = Depends(get_current_user)):
    service = GoogleCalendarService()
    try:
        events = service.fetch_events(user_id)
        return events
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to fetch events, please retry")
