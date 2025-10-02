from pydantic import BaseModel


class GoogleCalendarConnectResponse(BaseModel):
    """Response for Google Calendar OAuth initiation"""

    auth_url: str
    state: str


class GoogleCalendarCallbackRequest(BaseModel):
    """Request for Google Calendar OAuth callback"""

    code: str
