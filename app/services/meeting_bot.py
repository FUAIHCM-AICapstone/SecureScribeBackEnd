import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.constants.messages import MessageDescriptions
from app.core.config import settings
from app.crud.meeting_bot import crud_check_user_project_access, crud_create_bot_log, crud_create_meeting_bot, crud_delete_meeting_bot, crud_get_bot_logs, crud_get_meeting, crud_get_meeting_bot, crud_get_meeting_bot_by_meeting, crud_get_meeting_bots, crud_get_meeting_projects, crud_update_meeting_bot
from app.jobs.celery_worker import celery_app
from app.models.meeting import MeetingBot
from app.schemas.audio_file import AudioFileCreate
from app.schemas.meeting_bot import MeetingBotCreate, MeetingBotLogCreate, MeetingBotLogResponse, MeetingBotResponse, MeetingBotUpdate
from app.services.audio_file import create_audio_file


def create_meeting_bot(db: Session, bot_data: MeetingBotCreate, created_by: uuid.UUID) -> Any:
    meeting = crud_get_meeting(db, bot_data.meeting_id)
    if not meeting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=MessageDescriptions.MEETING_NOT_FOUND)
    existing_bot = crud_get_meeting_bot_by_meeting(db, bot_data.meeting_id)
    if existing_bot:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=MessageDescriptions.RESOURCE_ALREADY_EXISTS)
    return crud_create_meeting_bot(db, bot_data.meeting_id, bot_data.scheduled_start_time, bot_data.meeting_url, created_by)


def get_meeting_bot(db: Session, bot_id: uuid.UUID) -> Optional[Any]:
    return crud_get_meeting_bot(db, bot_id, include_relations=True)


def get_meeting_bot_by_meeting(db: Session, meeting_id: uuid.UUID) -> Optional[Any]:
    return crud_get_meeting_bot_by_meeting(db, meeting_id)


def get_meeting_bots(db: Session, user_id: uuid.UUID, page: int = 1, limit: int = 20) -> Tuple[List[Any], int]:
    bots, total = crud_get_meeting_bots(db, user_id, page, limit)
    for bot in bots:
        bot.logs.sort(key=lambda log: log.created_at, reverse=True)
    return bots, total


def update_meeting_bot(db: Session, bot_id: uuid.UUID, bot_data: MeetingBotUpdate, user_id: uuid.UUID) -> Optional[Any]:
    bot = crud_get_meeting_bot(db, bot_id, include_relations=False)
    if not bot:
        return None
    if bot.created_by != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=MessageDescriptions.MEETING_BOT_UNAUTHORIZED_UPDATE)
    return crud_update_meeting_bot(db, bot_id, **bot_data.model_dump(exclude_unset=True))


def delete_meeting_bot(db: Session, bot_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    bot = crud_get_meeting_bot(db, bot_id, include_relations=False)
    if not bot:
        return False
    if bot.created_by != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=MessageDescriptions.MEETING_BOT_UNAUTHORIZED_DELETE)
    return crud_delete_meeting_bot(db, bot_id)


def create_bot_log(db: Session, bot_id: uuid.UUID, log_data: MeetingBotLogCreate) -> Any:
    bot = crud_get_meeting_bot(db, bot_id, include_relations=False)
    if not bot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=MessageDescriptions.MEETING_BOT_NOT_FOUND)
    return crud_create_bot_log(db, bot_id, log_data.action, log_data.message)


def get_bot_logs(db: Session, bot_id: uuid.UUID, page: int = 1, limit: int = 50) -> Tuple[List[Any], int]:
    return crud_get_bot_logs(db, bot_id, page, limit)


def update_bot_status(db: Session, bot_id: uuid.UUID, status: str, error: Optional[str] = None, actual_start_time: Optional[datetime] = None, actual_end_time: Optional[datetime] = None) -> Optional[Any]:
    bot = crud_get_meeting_bot(db, bot_id, include_relations=False)
    if not bot:
        return None
    updates = {"status": status}
    if error:
        updates["last_error"] = error
        if status == "error":
            updates["retry_count"] = bot.retry_count + 1
    if actual_start_time:
        updates["actual_start_time"] = actual_start_time
    if actual_end_time:
        updates["actual_end_time"] = actual_end_time
    bot = crud_update_meeting_bot(db, bot_id, **updates)
    try:
        celery_app.send_task("app.jobs.tasks.send_bot_status_notification_task", args=[bot_id, status, error])
    except Exception:
        pass
    return bot


def process_bot_webhook_recording(db: Session, meeting_id: uuid.UUID, user_id: uuid.UUID, file_bytes: bytes) -> Dict[str, Any]:
    meeting = crud_get_meeting(db, meeting_id)
    if not meeting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=MessageDescriptions.MEETING_NOT_FOUND)
    audio_data = AudioFileCreate(meeting_id=meeting_id, uploaded_by=user_id)
    audio_file = create_audio_file(db, audio_data, file_bytes, "video/webm")
    if not audio_file:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=MessageDescriptions.MEETING_AUDIO_UPLOAD_FAILED)
    return {"audio_file_id": str(audio_file.id), "meeting_id": str(meeting_id)}


def trigger_meeting_bot_join(db: Session, meeting_id: uuid.UUID, user_id: uuid.UUID, bearer_token: str, meeting_url_override: Optional[str] = None, immediate: bool = False) -> Dict[str, Any]:
    meeting = crud_get_meeting(db, meeting_id)
    if not meeting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=MessageDescriptions.MEETING_NOT_FOUND)
    bot = crud_get_meeting_bot_by_meeting(db, meeting_id)
    bot_id = uuid.uuid4()
    if not bot:
        bot = crud_create_meeting_bot(db, meeting_id, None, None, user_id, bot_id, "pending")
    else:
        bot.id = bot_id
        db.commit()
        db.refresh(bot)
    is_creator = meeting.created_by == user_id
    project_ids = crud_get_meeting_projects(db, meeting_id) if not is_creator else []
    is_project_member = crud_check_user_project_access(db, user_id, project_ids) if project_ids else False
    if not is_creator and not is_project_member:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=MessageDescriptions.MEETING_BOT_UNAUTHORIZED_TRIGGER)
    meeting_url = meeting_url_override or bot.meeting_url or meeting.url
    if not meeting_url:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=MessageDescriptions.MEETING_URL_REQUIRED)
    if meeting_url_override or meeting.url:
        bot.meeting_url = meeting_url
    if not bearer_token or not bearer_token.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=MessageDescriptions.INVALID_BEARER_TOKEN_FORMAT)
    now = datetime.now(timezone.utc)
    status_val = "pending"
    scheduled_start_time = None
    if not immediate and bot.scheduled_start_time:
        if bot.scheduled_start_time < now:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=MessageDescriptions.MEETING_BOT_INVALID_SCHEDULED_TIME)
        status_val = "scheduled"
        scheduled_start_time = bot.scheduled_start_time
    crud_update_meeting_bot(db, bot.id, status=status_val)
    task = celery_app.send_task("app.jobs.tasks.schedule_meeting_bot_task", args=[str(meeting_id), str(user_id), bearer_token, meeting_url, bot_id], kwargs={"webhook_url": settings.BOT_WEBHOOK_URL})
    return {"task_id": task.id, "bot_id": bot_id, "meeting_id": str(meeting_id), "status": status_val, "scheduled_start_time": scheduled_start_time, "created_at": bot.created_at}


def serialize_meeting_bot(bot: MeetingBot) -> MeetingBotResponse:
    from app.schemas.meeting import MeetingResponse, ProjectResponse
    from app.schemas.user import UserResponse

    meeting_response = None
    if hasattr(bot, "meeting") and bot.meeting:
        meeting = bot.meeting
        creator = UserResponse.model_validate(meeting.created_by_user, from_attributes=True) if getattr(meeting, "created_by_user", None) else None
        projects = [ProjectResponse.model_validate(pm.project, from_attributes=True) for pm in meeting.projects if pm.project] if hasattr(meeting, "projects") and meeting.projects else []
        meeting_obj = MeetingResponse(id=meeting.id, title=meeting.title, description=meeting.description, url=meeting.url, start_time=meeting.start_time, created_by=meeting.created_by, is_personal=meeting.is_personal, status=meeting.status, is_deleted=meeting.is_deleted, created_at=meeting.created_at, updated_at=meeting.updated_at, projects=projects, creator=creator, can_access=True)
        meeting_response = meeting_obj.model_dump()
    return MeetingBotResponse(id=bot.id, meeting_id=bot.meeting_id, meeting=meeting_response, scheduled_start_time=bot.scheduled_start_time, actual_start_time=bot.actual_start_time, actual_end_time=bot.actual_end_time, status=bot.status, meeting_url=bot.meeting_url, retry_count=bot.retry_count, last_error=bot.last_error, created_by=bot.created_by, created_at=bot.created_at, updated_at=bot.updated_at, logs=[MeetingBotLogResponse.model_validate(log, from_attributes=True) for log in (bot.logs or [])])
