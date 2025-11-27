import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.events.domain_events import BaseDomainEvent
from app.models.user import User
from app.services.event_manager import EventManager
from app.services.user import create_user
from app.utils.auth import (
    create_access_token,
    create_refresh_token,
    get_firebase_user_info,
)


def firebase_login(db: Session, id_token: str):
    try:
        user_info = get_firebase_user_info(id_token)
        email = user_info.get("email")
        if not email:
            EventManager.emit_domain_event(
                BaseDomainEvent(
                    event_name="auth.login_failed",
                    actor_user_id=uuid.uuid4(),  # anonymous actor (token invalid)
                    target_type="auth",
                    target_id=None,
                    metadata={"reason": "email_missing"},
                )
            )
            raise HTTPException(status_code=400, detail="Email not found in Firebase token")

        user = db.query(User).filter(User.email == email).first()
        if not user:
            user_data = {
                "email": email,
                "name": user_info.get("name"),
                "avatar_url": user_info.get("picture"),
            }
            user = create_user(db, **user_data)

            from app.models.user import UserIdentity

            identity = UserIdentity(
                user_id=user.id,
                provider="google",
                provider_user_id=user_info.get("uid"),
                provider_email=email,
                provider_profile=user_info,
            )
            db.add(identity)
            db.commit()
        else:
            # Check if UserIdentity already exists for this user
            from app.models.user import UserIdentity

            existing_identity = db.query(UserIdentity).filter(UserIdentity.user_id == user.id, UserIdentity.provider == "google").first()
            if not existing_identity:
                identity = UserIdentity(
                    user_id=user.id,
                    provider="google",
                    provider_user_id=user_info.get("uid"),
                    provider_email=email,
                    provider_profile=user_info,
                )
                db.add(identity)
                db.commit()

        access_token = create_access_token({"sub": str(user.id)})
        refresh_token = create_refresh_token({"sub": str(user.id)})
        result = {
            "user": {"id": user.id, "email": user.email, "name": user.name},
            "token": {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            },
        }

        EventManager.emit_domain_event(
            BaseDomainEvent(
                event_name="auth.login_succeeded",
                actor_user_id=user.id,
                target_type="user",
                target_id=user.id,
                metadata={"provider": "google"},
            )
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        print(f"\033[91mError in firebase_login: {e}\033[0m")
        EventManager.emit_domain_event(
            BaseDomainEvent(
                event_name="auth.login_failed",
                actor_user_id=uuid.uuid4(),
                target_type="auth",
                target_id=None,
                metadata={"reason": "exception", "detail": str(e)},
            )
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google login service temporarily unavailable",
        )
