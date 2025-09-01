from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer
from firebase_admin import auth as firebase_auth
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import get_db
from app.models.user import User


def verify_google_token(id_token: str) -> dict:
    """
    Verify Google ID token and return decoded token payload.
    """
    try:
        decoded_token = firebase_auth.verify_id_token(id_token)
        return decoded_token
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid Google token: {str(e)}")


def get_google_user_info(id_token: str) -> dict:
    """
    Get user information from Google ID token.
    """
    decoded_token = verify_google_token(id_token)
    return {
        "uid": decoded_token.get("uid"),
        "email": decoded_token.get("email"),
        "name": decoded_token.get("name"),
        "picture": decoded_token.get("picture"),
    }


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")


def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")


def verify_token(token: str):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def get_current_user_from_token(token: str):
    payload = verify_token(token)
    if not payload or payload.get("type") != "access":
        return None
    return payload.get("sub")


class JWTBearer(HTTPBearer):
    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error, scheme_name="BearerAuth")

    async def __call__(self, request: Request) -> str:
        credentials = await super().__call__(request)
        if credentials:
            if not credentials.scheme.lower() == "bearer":
                raise HTTPException(
                    status_code=401, detail="Invalid authentication scheme"
                )
            if not self.verify_jwt(credentials.credentials):
                raise HTTPException(status_code=401, detail="Invalid token")
            return credentials.credentials
        else:
            raise HTTPException(status_code=401, detail="Invalid authorization code")

    def verify_jwt(self, token: str) -> bool:
        try:
            payload = verify_token(token)
            return payload is not None
        except Exception:
            return False


jwt_bearer = JWTBearer()


def get_current_user(token: str = Depends(jwt_bearer), db: Session = Depends(get_db)):
    """
    Extract user information from JWT token.
    """
    try:
        user_id = get_current_user_from_token(token)
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")

        user = db.query(User).filter(User.id == UUID(user_id)).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        return user
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail="Token verification failed") from e
