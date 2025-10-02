import json
import uuid
from typing import Any, Dict, List

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from app.core.config import settings
from app.db import get_session
from app.models.integration import Integration
from app.utils.redis import get_redis_client


def get_google_client_credentials() -> tuple[str, str, str]:
    """Load Google client credentials from the client secret file"""
    with open(settings.GOOGLE_CLIENT_SECRET_PATH) as f:
        client_secrets = json.load(f)

    # The file has a "web" key containing the credentials
    web_config = client_secrets.get("web", client_secrets)

    client_id = web_config["client_id"]
    client_secret = web_config["client_secret"]
    token_uri = web_config["token_uri"]

    return client_id, client_secret, token_uri


def create_oauth_flow() -> Flow:
    """Create OAuth flow for Google Calendar access"""
    return Flow.from_client_secrets_file(
        settings.GOOGLE_CLIENT_SECRET_PATH,
        scopes=[
            "openid",
            "https://www.googleapis.com/auth/userinfo.profile",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/calendar.readonly",
            "https://www.googleapis.com/auth/calendar",
        ],
        redirect_uri=f"{settings.SERVER_HOST}:{settings.SERVER_PORT}{settings.API_V1_STR}/auth/google/callback",
    )


def exchange_code_for_token(code: str) -> Credentials:
    """Exchange authorization code for credentials"""
    flow = create_oauth_flow()
    flow.fetch_token(code=code, access_type="offline", prompt="consent")
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
        return integration.credentials_meta.get("refresh_token") if integration else None
    finally:
        session.close()


def fetch_calendar_events(refresh_token: str) -> List[Dict[str, Any]]:
    """Fetch calendar events using refresh token"""
    client_id, client_secret, token_uri = get_google_client_credentials()

    credentials = Credentials(token=None, refresh_token=refresh_token, token_uri=token_uri, client_id=client_id, client_secret=client_secret)
    # Refresh access token using refresh token
    credentials.refresh(Request())

    service = build("calendar", "v3", credentials=credentials)
    events_result = service.events().list(calendarId="primary", maxResults=10, singleEvents=True, orderBy="startTime").execute()
    return events_result.get("items", [])


def store_oauth_state(state: str, user_id: uuid.UUID) -> None:
    """Store OAuth state and user_id mapping in Redis for callback retrieval"""
    redis_client = get_redis_client()
    key = f"oauth_state:{state}"
    print(f"\033[93m[GoogleCalendar] Storing OAuth state: {key} for user_id: {user_id}\033[0m")
    # Store for 10 minutes (600 seconds) - OAuth flow should complete within this time
    redis_client.setex(key, 600, str(user_id))


def get_user_id_from_state(state: str) -> uuid.UUID | None:
    """Retrieve user_id from Redis using OAuth state"""
    redis_client = get_redis_client()
    key = f"oauth_state:{state}"
    print(f"\033[93m[GoogleCalendar] Retrieving user_id from OAuth state: {key}\033[0m")
    user_id_str = redis_client.get(key)
    print(f"\033[93m[GoogleCalendar] Retrieved user_id from OAuth state: {user_id_str}\033[0m")
    if user_id_str:
        try:
            redis_client.delete(key)
            return uuid.UUID(user_id_str)
        except ValueError:
            redis_client.delete(key)
            return None

    return None
