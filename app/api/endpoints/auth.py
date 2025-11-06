from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import get_db
from app.models.user import User
from app.schemas.auth import (
    AuthResponse,
    GoogleAuthRequest,
    RefreshTokenRequest,
)
from app.schemas.common import ApiResponse
from app.schemas.user import UserUpdate
from app.services.auth import firebase_login
from app.services.user import update_user
from app.utils.auth import (
    create_access_token,
    get_current_user,
    verify_token,
)

router = APIRouter(prefix=settings.API_V1_STR, tags=["Auth"])
security = HTTPBearer()


@router.post("/auth/refresh", response_model=ApiResponse[dict])
def refresh_token_endpoint(request: RefreshTokenRequest):
    refresh_token = request.refresh_token

    print(f"\033[94m[INFO]\033[0m 🔄 Refresh token endpoint called")
    print(f"\033[93m[DEBUG]\033[0m Received refresh token: {refresh_token[:20]}...")

    try:
        payload = verify_token(refresh_token)

        if not payload or payload.get("type") != "refresh":
            print("\033[91m[ERROR]\033[0m ❌ Invalid refresh token - missing or wrong type")
            raise HTTPException(status_code=401, detail="Invalid refresh token")

        user_id = payload.get("sub")

        if not user_id:
            print("\033[91m[ERROR]\033[0m ❌ Invalid token payload - no user ID")
            raise HTTPException(status_code=401, detail="Invalid token payload")

        print(f"\033[92m[SUCCESS]\033[0m ✅ Token verified for user: {user_id}")
        access_token = create_access_token({"sub": user_id})

        print("\033[92m[SUCCESS]\033[0m ✅ New access token generated")
        print(f"\033[96m[INFO]\033[0m 📅 Token expires in {settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60} seconds")

        return ApiResponse(
            success=True,
            message="Token refreshed",
            data={
                "access_token": access_token,
                "token_type": "bearer",
                "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            },
        )
    except Exception as e:
        print(f"\033[91m[ERROR]\033[0m 💥 Exception during token refresh: {str(e)}")
        raise


@router.get("/me", response_model=ApiResponse[dict])
def get_current_user_info(current_user: User = Depends(get_current_user)):
    return ApiResponse(
        success=True,
        message="User information retrieved",
        data={
            "id": current_user.id,
            "email": current_user.email,
            "name": current_user.name,
            "avatar_url": current_user.avatar_url,
            "bio": current_user.bio,
            "position": current_user.position,
            "created_at": current_user.created_at,
            "updated_at": current_user.updated_at,
        },
    )


@router.put("/me", response_model=ApiResponse[dict])
def update_current_user_info(
    updates: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    update_data = updates.model_dump(exclude_unset=True)
    updated_user = update_user(db, current_user.id, **update_data)
    return ApiResponse(
        success=True,
        message="User information updated",
        data={
            "id": updated_user.id,
            "email": updated_user.email,
            "name": updated_user.name,
            "avatar_url": updated_user.avatar_url,
            "bio": updated_user.bio,
            "position": updated_user.position,
            "created_at": updated_user.created_at,
            "updated_at": updated_user.updated_at,
        },
    )


@router.post("/auth/firebase/login", response_model=ApiResponse[AuthResponse])
def firebase_login_endpoint(request: GoogleAuthRequest, db: Session = Depends(get_db)):
    try:
        result = firebase_login(db, request.id_token)
        return ApiResponse(success=True, message="Firebase login successful", data=result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
