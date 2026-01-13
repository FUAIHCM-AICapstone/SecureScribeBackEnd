import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from app.models.meeting import Meeting, MeetingBot, MeetingBotLog, ProjectMeeting
from app.models.project import UserProject
from app.schemas.meeting_bot import MeetingBotCreate, MeetingBotLogCreate, MeetingBotLogResponse, MeetingBotResponse, MeetingBotUpdate


def create_meeting_bot(db: Session, bot_data: MeetingBotCreate, created_by: uuid.UUID) -> MeetingBot:
    meeting = db.query(Meeting).filter(Meeting.id == bot_data.meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    existing_bot = db.query(MeetingBot).filter(MeetingBot.meeting_id == bot_data.meeting_id).first()
    if existing_bot:
        raise HTTPException(status_code=400, detail="Meeting bot already exists for this meeting")
    bot = MeetingBot(meeting_id=bot_data.meeting_id, scheduled_start_time=bot_data.scheduled_start_time, meeting_url=bot_data.meeting_url, created_by=created_by)
    db.add(bot)
    db.commit()
    db.refresh(bot)
    return bot

def get_meeting_bot(db: Session, bot_id: uuid.UUID, user_id: uuid.UUID) -> Optional[MeetingBot]:
    return db.query(MeetingBot).options(joinedload(MeetingBot.logs), joinedload(MeetingBot.meeting).joinedload(Meeting.projects).joinedload(ProjectMeeting.project), joinedload(MeetingBot.meeting).joinedload(Meeting.created_by_user)).filter(MeetingBot.id == bot_id).first()

def get_meeting_bot_by_meeting(db: Session, meeting_id: uuid.UUID, user_id: uuid.UUID) -> Optional[MeetingBot]:
    return db.query(MeetingBot).options(joinedload(MeetingBot.logs), joinedload(MeetingBot.meeting).joinedload(Meeting.projects).joinedload(ProjectMeeting.project), joinedload(MeetingBot.meeting).joinedload(Meeting.created_by_user)).filter(MeetingBot.meeting_id == meeting_id).first()

def get_meeting_bots(db: Session, user_id: uuid.UUID, page: int = 1, limit: int = 20) -> Tuple[List[MeetingBot], int]:
    offset = (page - 1) * limit
    query = db.query(MeetingBot).options(joinedload(MeetingBot.logs), joinedload(MeetingBot.meeting).joinedload(Meeting.projects).joinedload(ProjectMeeting.project), joinedload(MeetingBot.meeting).joinedload(Meeting.created_by_user)).filter(MeetingBot.created_by == user_id).order_by(MeetingBot.created_at.desc())
    total = query.count()
    bots = query.offset(offset).limit(limit).all()
    for bot in bots:
        bot.logs.sort(key=lambda log: log.created_at, reverse=True)
    return bots, total

def update_meeting_bot(db: Session, bot_id: uuid.UUID, bot_data: MeetingBotUpdate, user_id: uuid.UUID) -> Optional[MeetingBot]:
    bot = db.query(MeetingBot).filter(MeetingBot.id == bot_id).first()
    if not bot:
        return None
    if bot.created_by != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to update this bot")
    for field, value in bot_data.model_dump(exclude_unset=True).items():
        setattr(bot, field, value)
    bot.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(bot)
    return bot

def delete_meeting_bot(db: Session, bot_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    bot = db.query(MeetingBot).filter(MeetingBot.id == bot_id).first()
    if not bot:
        return False
    if bot.created_by != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this bot")
    db.query(MeetingBotLog).filter(MeetingBotLog.meeting_bot_id == bot_id).delete()
    db.delete(bot)
    db.commit()
    return True

def create_bot_log(db: Session, bot_id: uuid.UUID, log_data: MeetingBotLogCreate) -> MeetingBotLog:
    bot = db.query(MeetingBot).filter(MeetingBot.id == bot_id).first()
    if not bot:
        raise HTTPException(status_code=404, detail="Meeting bot not found")
    log = MeetingBotLog(meeting_bot_id=bot_id, action=log_data.action, message=log_data.message)
    db.add(log)
    db.commit()
    db.refresh(log)
    return log

def get_bot_logs(db: Session, bot_id: uuid.UUID, page: int = 1, limit: int = 50) -> Tuple[List[MeetingBotLog], int]:
    offset = (page - 1) * limit
    query = db.query(MeetingBotLog).filter(MeetingBotLog.meeting_bot_id == bot_id).order_by(MeetingBotLog.created_at.desc())
    total = query.count()
    logs = query.offset(offset).limit(limit).all()
    return logs, total

def update_bot_status(db: Session, bot_id: uuid.UUID, status: str, error: Optional[str] = None, actual_start_time: Optional[datetime] = None, actual_end_time: Optional[datetime] = None) -> Optional[MeetingBot]:
    bot = db.query(MeetingBot).filter(MeetingBot.id == bot_id).first()
    if not bot:
        return None
    bot.status = status
    if error:
        bot.last_error = error
        if status == "error":
            bot.retry_count += 1
    if actual_start_time:
        bot.actual_start_time = actual_start_time
    if actual_end_time:
        bot.actual_end_time = actual_end_time
    bot.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(bot)
    try:
        from app.jobs.celery_worker import celery_app
        celery_app.send_task("app.jobs.tasks.send_bot_status_notification_task", args=[bot_id, status, error])
    except Exception:
        pass
    return bot

def process_bot_webhook_recording(db: Session, meeting_id: uuid.UUID, user_id: uuid.UUID, file_bytes: bytes) -> Dict[str, Any]:
    from app.schemas.audio_file import AudioFileCreate
    from app.services.audio_file import create_audio_file
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id, Meeting.is_deleted == False).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    audio_data = AudioFileCreate(meeting_id=meeting_id, uploaded_by=user_id)
    audio_file = create_audio_file(db, audio_data, file_bytes, "video/webm")
    if not audio_file:
        raise HTTPException(status_code=500, detail="Failed to store audio file")
    return {"audio_file_id": str(audio_file.id), "meeting_id": str(meeting_id)}

def trigger_meeting_bot_join(db: Session, meeting_id: uuid.UUID, user_id: uuid.UUID, bearer_token: str, meeting_url_override: Optional[str] = None, immediate: bool = False) -> Dict[str, Any]:
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id, Meeting.is_deleted == False).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    bot = db.query(MeetingBot).filter(MeetingBot.meeting_id == meeting_id).first()
    bot_id = str(uuid.uuid4())
    if not bot:
        bot = MeetingBot(id=uuid.UUID(bot_id), meeting_id=meeting_id, created_by=user_id, status="pending")
        db.add(bot)
        db.commit()
        db.refresh(bot)
    else:
        bot.id = uuid.UUID(bot_id)
        db.commit()
        db.refresh(bot)
    is_creator = meeting.created_by == user_id
    is_project_member = False
    if not is_creator:
        project_ids = db.query(ProjectMeeting.project_id).filter(ProjectMeeting.meeting_id == meeting_id).all()
        if project_ids:
            project_id_list = [p[0] for p in project_ids]
            is_project_member = db.query(UserProject).filter(UserProject.user_id == user_id, UserProject.project_id.in_(project_id_list)).first() is not None
    if not is_creator and not is_project_member:
        raise HTTPException(status_code=403, detail="Not authorized to trigger bot for this meeting")
    meeting_url = meeting_url_override or bot.meeting_url or meeting.url
    if not meeting_url:
        raise HTTPException(status_code=400, detail="Meeting URL is required")
    if meeting_url_override or meeting.url:
        bot.meeting_url = meeting_url
    if not bearer_token or not bearer_token.strip():
        raise HTTPException(status_code=400, detail="Invalid bearer token format")
    now = datetime.now(timezone.utc)
    if immediate:
        status = "pending"
        scheduled_start_time = None
    else:
        if bot.scheduled_start_time:
            if bot.scheduled_start_time < now:
                raise HTTPException(status_code=400, detail="Scheduled start time cannot be in the past")
            status = "scheduled"
            scheduled_start_time = bot.scheduled_start_time
        else:
            status = "pending"
            scheduled_start_time = None
    bot.status = status
    bot.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(bot)
    from app.core.config import settings
    from app.jobs.celery_worker import celery_app
    task = celery_app.send_task("app.jobs.tasks.schedule_meeting_bot_task", args=[str(meeting_id), str(user_id), bearer_token, meeting_url, bot_id], kwargs={"webhook_url": settings.BOT_WEBHOOK_URL})
    return {"task_id": task.id, "bot_id": bot_id, "meeting_id": str(meeting_id), "status": status, "scheduled_start_time": scheduled_start_time, "created_at": bot.created_at}

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
