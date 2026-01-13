from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.events.domain_events import BaseDomainEvent
from app.models.user import User, UserIdentity
from app.services.event_manager import EventManager
from app.services.user import create_user
from app.utils.auth import create_access_token, create_refresh_token, get_firebase_user_info


def firebase_login(db: Session, id_token: str):
    user_info = get_firebase_user_info(id_token)
    email = user_info.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Email not found in Firebase token")
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = create_user(db, email=email, name=user_info.get("name"), avatar_url=user_info.get("picture"))
        identity = UserIdentity(user_id=user.id, provider="google", provider_user_id=user_info.get("uid"), provider_email=email, provider_profile=user_info)
        db.add(identity)
        db.commit()
    else:
        identity = db.query(UserIdentity).filter(UserIdentity.user_id == user.id, UserIdentity.provider == "google").first()
        if not identity:
            identity = UserIdentity(user_id=user.id, provider="google", provider_user_id=user_info.get("uid"), provider_email=email, provider_profile=user_info)
            db.add(identity)
            db.commit()
    EventManager.emit_domain_event(BaseDomainEvent(event_name="auth.login_succeeded", actor_user_id=user.id, target_type="user", target_id=user.id, metadata={"provider": "google"}))
    return {"user": {"id": user.id, "email": user.email, "name": user.name}, "token": {"access_token": create_access_token({"sub": str(user.id)}), "refresh_token": create_refresh_token({"sub": str(user.id)}), "token_type": "bearer", "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60}}
