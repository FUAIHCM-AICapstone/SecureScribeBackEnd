from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.user import User
from app.services.user import check_email_exists, create_user
from app.utils.auth import create_access_token, create_refresh_token
from app.utils.password import verify_password


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    try:
        user = db.query(User).filter(User.email == email).first()
        if (
            user
            and user.password_hash
            and verify_password(password, user.password_hash)
        ):
            return user
        return None
    except Exception:
        # Log the error but don't expose internal details
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service temporarily unavailable",
        )


def register_user(db: Session, **user_data) -> User:
    email = user_data.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email is required"
        )

    # Check if email already exists
    if check_email_exists(db, email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
        )

    try:
        return create_user(db, **user_data)
    except IntegrityError as e:
        db.rollback()
        # Handle specific database constraint violations
        error_msg = str(e).lower()
        if "unique constraint" in error_msg or "duplicate key" in error_msg:
            if "email" in error_msg:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Email already registered",
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="User data conflicts with existing records",
                )
        elif "foreign key" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid reference data provided",
            )
        elif "check constraint" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User data violates validation rules",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database constraint violation occurred",
            )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}",
        )


def login_user(db: Session, email: str, password: str):
    try:
        user = authenticate_user(db, email, password)
        if not user:
            return None
        access_token = create_access_token({"sub": str(user.id)})
        refresh_token = create_refresh_token({"sub": str(user.id)})
        return {
            "user": {"id": user.id, "email": user.email, "name": user.name},
            "token": {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            },
        }
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login service temporarily unavailable",
        )
