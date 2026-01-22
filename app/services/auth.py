from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.constants.messages import MessageDescriptions
from app.core.azure_oauth_utils import azure_oauth_utils_manager
from app.core.config import settings
from app.crud.user import crud_get_user_by_email
from app.events.domain_events import BaseDomainEvent
from app.models.user import UserIdentity
from app.services.event_manager import EventManager
from app.services.user import create_user
from app.utils.auth import create_access_token, create_refresh_token


def azure_login(db: Session, code: str):
    """Handle Azure AD OAuth login"""
    try:
        # Exchange authorization code for tokens
        token_response = azure_oauth_utils_manager.acquire_token_by_authorization_code(code)
        access_token = token_response.get("access_token")

        if not access_token:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=MessageDescriptions.AUTH_FAILED)

        # Get user information from Microsoft Graph
        user_info = azure_oauth_utils_manager.get_user_info(access_token)
        email = user_info.get("mail") or user_info.get("userPrincipalName")

        if not email:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=MessageDescriptions.AUTH_EMAIL_NOT_FOUND)

        user = crud_get_user_by_email(db, email)
        if not user:
            user = create_user(db, email=email, name=user_info.get("displayName"), avatar_url=user_info.get("picture"))
            identity = UserIdentity(user_id=user.id, provider="azure", provider_user_id=user_info.get("id"), provider_email=email, provider_profile=user_info)
            db.add(identity)
            db.commit()
        else:
            identity = db.query(UserIdentity).filter(UserIdentity.user_id == user.id, UserIdentity.provider == "azure").first()
            if not identity:
                identity = UserIdentity(user_id=user.id, provider="azure", provider_user_id=user_info.get("id"), provider_email=email, provider_profile=user_info)
                db.add(identity)
                db.commit()

        EventManager.emit_domain_event(BaseDomainEvent(event_name="auth.login_succeeded", actor_user_id=user.id, target_type="user", target_id=user.id, metadata={"provider": "azure"}))

        return {"user": {"id": user.id, "email": user.email, "name": user.name}, "token": {"access_token": create_access_token({"sub": str(user.id)}), "refresh_token": create_refresh_token({"sub": str(user.id)}), "token_type": "bearer", "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60}}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
