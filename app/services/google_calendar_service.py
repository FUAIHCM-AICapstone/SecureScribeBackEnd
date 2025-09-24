import uuid
from typing import Dict, List, Any
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from fastapi import HTTPException
from app.core.config import settings
from app.models.integration import Integration
from app.db import get_session
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)

class GoogleAuthError(Exception):
    pass

class TokenExpiredError(Exception):
    pass

class RevokedAccessError(Exception):
    pass

class GoogleCalendarService:
    SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

    def initiate_oauth_flow(self, user_id: uuid.UUID) -> Dict[str, str]:
        flow = Flow.from_client_secrets_file(
            settings.GOOGLE_CLIENT_SECRET_PATH,
            scopes=self.SCOPES,
            redirect_uri=f"{settings.SERVER_HOST}:{settings.SERVER_PORT}{settings.API_V1_STR}/auth/google/callback"
        )
        auth_url, state = flow.authorization_url(access_type="offline", include_granted_scopes="true")
        return {"auth_url": auth_url, "state": state}

    def handle_oauth_callback(self, code: str, user_id: uuid.UUID) -> bool:
        try:
            flow = Flow.from_client_secrets_file(
                settings.GOOGLE_CLIENT_SECRET_PATH,
                scopes=self.SCOPES,
                redirect_uri=f"{settings.SERVER_HOST}:{settings.SERVER_PORT}{settings.API_V1_STR}/auth/google/callback"
            )
            flow.fetch_token(code=code)
            credentials = flow.credentials
            refresh_token = credentials.refresh_token
            if not refresh_token:
                raise GoogleAuthError("No refresh token received from Google")
            with get_session() as session:
                integration = session.query(Integration).filter(Integration.user_id == user_id, Integration.type == "google_calendar").first()
                if not integration:
                    integration = Integration(user_id=user_id, type="google_calendar", credentials_meta={"refresh_token": refresh_token})
                    session.add(integration)
                else:
                    integration.credentials_meta = {"refresh_token": refresh_token}
                session.commit()
            logger.info(f"Google Calendar connected for user {user_id}")
            return True
        except GoogleAuthError as e:
            logger.error(f"Google auth error: {str(e)}")
            raise HTTPException(status_code=400, detail="Connection failed, please retry") from e
        except Exception as e:
            logger.error(f"OAuth callback failed: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal error, please try again") from e

    def fetch_events(self, user_id: uuid.UUID) -> List[Dict[str, Any]]:
        with get_session() as session:
            integration = session.query(Integration).filter(Integration.user_id == user_id, Integration.type == "google_calendar").first()
            if not integration or not integration.credentials_meta.get("refresh_token"):
                raise HTTPException(status_code=400, detail="Google Calendar not connected, please connect first")
            refresh_token = integration.credentials_meta["refresh_token"]
            creds = Credentials(token=None, refresh_token=refresh_token, client_id=None, client_secret=None)
            for attempt in range(3):
                try:
                    creds.refresh()
                    service = build("calendar", "v3", credentials=creds)
                    events_result = service.events().list(calendarId="primary", maxResults=10).execute()
                    return events_result.get("items", [])
                except Exception as e:
                    logger.error(f"Fetch events attempt {attempt+1} failed: {str(e)}")
                    if attempt == 2:
                        if "Token has been expired" in str(e):
                            raise HTTPException(status_code=401, detail="Access revoked, please reconnect") from e
                        raise HTTPException(status_code=500, detail="Failed to fetch events after retries") from e

    def refresh_access_token(self, user_id: uuid.UUID) -> bool:
        with get_session() as session:
            integration = session.query(Integration).filter(Integration.user_id == user_id, Integration.type == "google_calendar").first()
            if not integration or not integration.credentials_meta.get("refresh_token"):
                logger.warning(f"No integration or refresh token for user {user_id}")
                return False
            refresh_token = integration.credentials_meta["refresh_token"]
            creds = Credentials(token=None, refresh_token=refresh_token, client_id=None, client_secret=None)
            try:
                creds.refresh()
                logger.info(f"Token refreshed for user {user_id}")
                return True
            except Exception as e:
                logger.error(f"Refresh token failed for user {user_id}: {str(e)}")
                # If revoked, disable
                if "Token has been expired" in str(e):
                    integration.credentials_meta = {}
                    session.commit()
                    logger.info(f"Disabled integration for user {user_id} due to revoked access")
                return False
