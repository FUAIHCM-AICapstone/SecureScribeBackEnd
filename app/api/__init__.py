from fastapi import APIRouter

from app.api.endpoints.auth import router as auth_router
from app.api.endpoints.meeting import router as meeting_router
from app.api.endpoints.notificaiton import router as notification_router
from app.api.endpoints.project import router as project_router
from app.api.endpoints.user import router as user_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(user_router)
api_router.include_router(project_router)
api_router.include_router(meeting_router)
api_router.include_router(notification_router)
