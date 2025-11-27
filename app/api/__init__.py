from fastapi import APIRouter

from app.api.endpoints.audio_file import router as audio_file_router
from app.api.endpoints.auth import router as auth_router
from app.api.endpoints.chat import router as chat_router
from app.api.endpoints.conversation import router as conversation_router
from app.api.endpoints.file import router as file_router
from app.api.endpoints.meeting import router as meeting_router
from app.api.endpoints.meeting_bot import router as meeting_bot_router
from app.api.endpoints.meeting_note import router as meeting_note_router
from app.api.endpoints.notification import router as notification_router
from app.api.endpoints.project import router as project_router
from app.api.endpoints.search import router as search_router
from app.api.endpoints.statistics import router as statistics_router
from app.api.endpoints.task import router as task_router
from app.api.endpoints.transcript import router as transcript_router
from app.api.endpoints.user import router as user_router
from app.api.endpoints.webhook import router as webhook_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(user_router)
api_router.include_router(chat_router)
api_router.include_router(project_router)
api_router.include_router(meeting_router)
api_router.include_router(meeting_note_router)
api_router.include_router(meeting_bot_router)
api_router.include_router(file_router)
api_router.include_router(audio_file_router)
api_router.include_router(transcript_router)
api_router.include_router(webhook_router)
api_router.include_router(search_router)
api_router.include_router(notification_router)
api_router.include_router(task_router)
api_router.include_router(conversation_router)
api_router.include_router(statistics_router)
