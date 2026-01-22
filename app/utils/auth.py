from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import get_db
from app.models.user import User


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")


def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES))
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
    except Exception:
        return None


def get_current_user_from_token(token: str):
    payload = verify_token(token)

    if not payload:
        return None

    token_type = payload.get("type")

    if token_type != "access":
        return None

    user_id = payload.get("sub")
    return user_id


class JWTBearer(HTTPBearer):
    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error, scheme_name="BearerAuth")

    async def __call__(self, request: Request) -> str:
        authorization = request.headers.get("Authorization")
        if not authorization:
            raise HTTPException(status_code=403, detail="Authentication required")

        # Parse the authorization header
        try:
            scheme, credentials = authorization.split(" ", 1)
        except ValueError:
            raise HTTPException(status_code=403, detail="Invalid authentication scheme")

        if scheme.lower() != "bearer":
            raise HTTPException(status_code=403, detail="Invalid authentication scheme")

        # Return the token - verification will happen in get_current_user
        return credentials


jwt_bearer = JWTBearer()


def get_current_user(token: str = Depends(jwt_bearer), db: Session = Depends(get_db)):
    """
    Extract user information from JWT token.
    """
    try:
        # Strip Bearer prefix if present (for direct calls to this function)
        import re

        token = re.sub(r"^[Bb]earer\s+", "", token).strip()

        user_id = get_current_user_from_token(token)
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")

        user = db.query(User).filter(User.id == int(user_id)).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        return user
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail="Token verification failed") from e
