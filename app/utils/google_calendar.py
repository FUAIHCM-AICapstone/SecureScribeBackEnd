import uuid
from typing import Any, Dict, List

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from app.core.config import settings
from app.db import get_session
from app.models.integration import Integration


def create_oauth_flow() -> Flow:
    """Create OAuth flow for Google Calendar access"""
    return Flow.from_client_secrets_file(
        settings.GOOGLE_CLIENT_SECRET_PATH,
        scopes=["https://www.googleapis.com/auth/calendar.readonly"],
        redirect_uri=f"{settings.SERVER_HOST}:{settings.SERVER_PORT}{settings.API_V1_STR}/auth/google/callback",
    )


def exchange_code_for_token(code: str) -> Credentials:
    """Exchange authorization code for credentials"""
    flow = create_oauth_flow()
    flow.fetch_token(code=code)
    return flow.credentials


def store_refresh_token(user_id: uuid.UUID, refresh_token: str) -> bool:
    """Store refresh token in database"""
    session = get_session()
    try:
        integration = (
            session.query(Integration)
            .filter(
                Integration.user_id == user_id,
                Integration.type == "google_calendar",
            )
            .first()
        )

        if not integration:
            integration = Integration(
                user_id=user_id,
                type="google_calendar",
                credentials_meta={"refresh_token": refresh_token},
            )
            session.add(integration)
        else:
            integration.credentials_meta = {"refresh_token": refresh_token}

        session.commit()
        return True
    finally:
        session.close()


def get_refresh_token(user_id: uuid.UUID) -> str | None:
    """Get refresh token for user"""
    session = get_session()
    try:
        integration = (
            session.query(Integration)
            .filter(
                Integration.user_id == user_id,
                Integration.type == "google_calendar",
            )
            .first()
        )
        return (
            integration.credentials_meta.get("refresh_token") if integration else None
        )
    finally:
        session.close()


def fetch_calendar_events(refresh_token: str) -> List[Dict[str, Any]]:
    """Fetch calendar events using refresh token"""
    credentials = Credentials(
        token=None, refresh_token=refresh_token, client_id=None, client_secret=None
    )
    credentials.refresh()

    service = build("calendar", "v3", credentials=credentials)
    events_result = service.events().list(calendarId="primary", maxResults=10).execute()
    return events_result.get("items", [])
