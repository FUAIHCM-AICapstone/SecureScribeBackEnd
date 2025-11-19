import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from app.models.meeting import Meeting, MeetingBot, MeetingBotLog
from app.models.project import UserProject
from app.schemas.meeting_bot import MeetingBotCreate, MeetingBotUpdate, MeetingBotLogCreate


def create_meeting_bot(db: Session, bot_data: MeetingBotCreate, created_by: uuid.UUID) -> MeetingBot:
    """Create new meeting bot"""
    meeting = db.query(Meeting).filter(Meeting.id == bot_data.meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    existing_bot = db.query(MeetingBot).filter(MeetingBot.meeting_id == bot_data.meeting_id).first()
    if existing_bot:
        raise HTTPException(status_code=400, detail="Meeting bot already exists for this meeting")

    bot = MeetingBot(
        meeting_id=bot_data.meeting_id,
        scheduled_start_time=bot_data.scheduled_start_time,
        meeting_url=bot_data.meeting_url,
        created_by=created_by,
    )

    db.add(bot)
    db.commit()
    db.refresh(bot)
    return bot


def get_meeting_bot(db: Session, bot_id: uuid.UUID, user_id: uuid.UUID) -> Optional[MeetingBot]:
    """Get meeting bot by ID"""
    bot = db.query(MeetingBot).options(joinedload(MeetingBot.logs), joinedload(MeetingBot.meeting)).filter(MeetingBot.id == bot_id).first()
    return bot


def get_meeting_bot_by_meeting(db: Session, meeting_id: uuid.UUID, user_id: uuid.UUID) -> Optional[MeetingBot]:
    """Get meeting bot by meeting ID"""
    bot = db.query(MeetingBot).options(joinedload(MeetingBot.logs)).filter(MeetingBot.meeting_id == meeting_id).first()
    return bot


def get_meeting_bots(db: Session, user_id: uuid.UUID, page: int = 1, limit: int = 20) -> Tuple[List[MeetingBot], int]:
    """Get meeting bots with pagination"""
    offset = (page - 1) * limit

    query = db.query(MeetingBot).options(joinedload(MeetingBot.logs), joinedload(MeetingBot.meeting)).filter(MeetingBot.created_by == user_id)

    total = query.count()
    bots = query.offset(offset).limit(limit).all()

    return bots, total


def update_meeting_bot(db: Session, bot_id: uuid.UUID, bot_data: MeetingBotUpdate, user_id: uuid.UUID) -> Optional[MeetingBot]:
    """Update meeting bot"""
    bot = db.query(MeetingBot).filter(MeetingBot.id == bot_id).first()
    if not bot:
        return None

    if bot.created_by != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to update this bot")

    for field, value in bot_data.model_dump(exclude_unset=True).items():
        setattr(bot, field, value)

    bot.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(bot)
    return bot


def delete_meeting_bot(db: Session, bot_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    """Delete meeting bot"""
    bot = db.query(MeetingBot).filter(MeetingBot.id == bot_id).first()
    if not bot:
        return False

    if bot.created_by != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this bot")

    db.delete(bot)
    db.commit()
    return True


def create_bot_log(db: Session, bot_id: uuid.UUID, log_data: MeetingBotLogCreate) -> MeetingBotLog:
    """Create bot log entry"""
    bot = db.query(MeetingBot).filter(MeetingBot.id == bot_id).first()
    if not bot:
        raise HTTPException(status_code=404, detail="Meeting bot not found")

    log = MeetingBotLog(
        meeting_bot_id=bot_id,
        action=log_data.action,
        message=log_data.message,
    )

    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def get_bot_logs(db: Session, bot_id: uuid.UUID, page: int = 1, limit: int = 50) -> Tuple[List[MeetingBotLog], int]:
    """Get bot logs with pagination"""
    offset = (page - 1) * limit

    query = db.query(MeetingBotLog).filter(MeetingBotLog.meeting_bot_id == bot_id).order_by(MeetingBotLog.created_at.desc())

    total = query.count()
    logs = query.offset(offset).limit(limit).all()

    return logs, total


def update_bot_status(db: Session, bot_id: uuid.UUID, status: str, error: Optional[str] = None) -> Optional[MeetingBot]:
    """Update bot status and increment retry count if needed"""
    bot = db.query(MeetingBot).filter(MeetingBot.id == bot_id).first()
    if not bot:
        return None

    bot.status = status
    if error:
        bot.last_error = error
        if status == "failed":
            bot.retry_count += 1

    bot.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(bot)
    return bot


def process_bot_webhook_recording(
    db: Session,
    meeting_id: uuid.UUID,
    user_id: uuid.UUID,
    file_bytes: bytes,
) -> Dict[str, Any]:
    """
    Process bot webhook recording and create audio file.

    Args:
        db: Database session
        meeting_id: UUID of the meeting
        user_id: UUID of the user (from bearer token)
        file_bytes: Binary audio file data

    Returns:
        Dictionary with audio_file_id and task_id for processing

    Raises:
        HTTPException: For validation failures
    """
    from app.models.meeting import AudioFile
    from app.schemas.audio_file import AudioFileCreate
    from app.services.audio_file import create_audio_file

    print(f"\033[94m🎥 [SERVICE] Processing webhook recording for meeting {meeting_id}\033[0m")

    # Validate meeting exists
    print(f"\033[93m📋 [SERVICE] Validating meeting exists\033[0m")
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id, Meeting.is_deleted == False).first()

    if not meeting:
        print(f"\033[91m❌ [SERVICE] Meeting not found: {meeting_id}\033[0m")
        raise HTTPException(status_code=404, detail="Meeting not found")

    print(f"\033[92m✅ [SERVICE] Meeting validated: {meeting.title}\033[0m")

    # Create audio file record
    print(f"\033[93m📋 [SERVICE] Creating audio file record\033[0m")
    audio_data = AudioFileCreate(meeting_id=meeting_id, uploaded_by=user_id)
    audio_file = create_audio_file(db, audio_data, file_bytes, "video/webm")

    if not audio_file:
        print(f"\033[91m❌ [SERVICE] Failed to store audio file\033[0m")
        raise HTTPException(status_code=500, detail="Failed to store audio file")

    print(f"\033[92m✅ [SERVICE] Audio file created successfully - id: {audio_file.id}\033[0m")

    return {
        "audio_file_id": str(audio_file.id),
        "meeting_id": str(meeting_id),
    }


def trigger_meeting_bot_join(
    db: Session,
    meeting_id: uuid.UUID,
    user_id: uuid.UUID,
    bearer_token: str,
    meeting_url_override: Optional[str] = None,
    immediate: bool = False,
) -> Dict[str, Any]:
    """
    Trigger bot to join meeting and return task info.

    Implements the following validations and logic:
    - Meeting validation (exists, not deleted)
    - MeetingBot validation (exists for meeting)
    - Authorization check (user is creator or project member)
    - Meeting URL resolution (from MeetingBot or request override)
    - Bearer token validation (not empty, proper format)
    - Scheduling logic (immediate vs scheduled with time validation)
    - MeetingBot status update (pending or scheduled)
    - Celery task queuing with proper parameters

    Args:
        db: Database session
        meeting_id: UUID of the meeting
        user_id: UUID of the user triggering the join
        bearer_token: Bearer token for bot service authentication
        meeting_url_override: Optional meeting URL override from request
        immediate: Whether to join immediately or use scheduled time

    Returns:
        Dictionary with task_id, bot_id, meeting_id, status, scheduled_start_time, created_at

    Raises:
        HTTPException: For various validation failures
    """
    print(f"\033[94m🤖 [SERVICE] Triggering bot join for meeting {meeting_id}\033[0m")
    
    # 1. Meeting validation (exists, not deleted)
    print(f"\033[93m📋 [SERVICE] Validating meeting exists\033[0m")
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id, Meeting.is_deleted == False).first()

    if not meeting:
        print(f"\033[91m❌ [SERVICE] Meeting not found: {meeting_id}\033[0m")
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    print(f"\033[92m✅ [SERVICE] Meeting validated: {meeting.title}\033[0m")

    # 2. MeetingBot validation (exists for meeting)
    print(f"\033[93m📋 [SERVICE] Validating meeting bot exists\033[0m")
    bot = db.query(MeetingBot).filter(MeetingBot.meeting_id == meeting_id).first()

    if not bot:
        print(f"\033[91m❌ [SERVICE] Meeting bot not found for meeting: {meeting_id}\033[0m")
        raise HTTPException(status_code=404, detail="Meeting bot not found for this meeting")

    print(f"\033[92m✅ [SERVICE] Meeting bot validated: {bot.id}\033[0m")

    # 3. Authorization check (user is creator or project member)
    print(f"\033[93m📋 [SERVICE] Checking authorization\033[0m")
    is_creator = meeting.created_by == user_id
    is_project_member = False

    if not is_creator:
        # Check if user is a member of any project associated with the meeting
        from app.models.meeting import ProjectMeeting

        project_ids = db.query(ProjectMeeting.project_id).filter(ProjectMeeting.meeting_id == meeting_id).all()

        if project_ids:
            project_id_list = [p[0] for p in project_ids]
            is_project_member = db.query(UserProject).filter(UserProject.user_id == user_id, UserProject.project_id.in_(project_id_list)).first() is not None

    if not is_creator and not is_project_member:
        print(f"\033[91m❌ [SERVICE] User not authorized for meeting: {user_id}\033[0m")
        raise HTTPException(status_code=403, detail="Not authorized to trigger bot for this meeting")
    
    print(f"\033[92m✅ [SERVICE] User authorized (creator: {is_creator}, project_member: {is_project_member})\033[0m")

    # 4. Meeting URL resolution (from MeetingBot or request override)
    print(f"\033[93m📋 [SERVICE] Resolving meeting URL\033[0m")
    meeting_url = meeting_url_override or bot.meeting_url

    if not meeting_url:
        print(f"\033[91m❌ [SERVICE] Meeting URL is required\033[0m")
        raise HTTPException(status_code=400, detail="Meeting URL is required")
    
    print(f"\033[92m✅ [SERVICE] Meeting URL resolved: {meeting_url}\033[0m")

    # 5. Bearer token validation (not empty, proper format)
    print(f"\033[93m📋 [SERVICE] Validating bearer token\033[0m")
    if not bearer_token or not bearer_token.strip():
        print(f"\033[91m❌ [SERVICE] Invalid bearer token format\033[0m")
        raise HTTPException(status_code=400, detail="Invalid bearer token format")
    
    print(f"\033[92m✅ [SERVICE] Bearer token validated\033[0m")

    # 6. Scheduling logic (immediate vs scheduled with time validation)
    print(f"\033[93m📋 [SERVICE] Determining scheduling logic (immediate: {immediate})\033[0m")
    now = datetime.utcnow()

    if immediate:
        # Immediate join - set status to pending
        status = "pending"
        scheduled_start_time = None
        print(f"\033[92m✅ [SERVICE] Immediate join - status: pending\033[0m")
    else:
        # Check if bot has scheduled_start_time
        if bot.scheduled_start_time:
            # Validate scheduled time is not in the past
            if bot.scheduled_start_time < now:
                print(f"\033[91m❌ [SERVICE] Scheduled time in the past: {bot.scheduled_start_time}\033[0m")
                raise HTTPException(status_code=400, detail="Scheduled start time cannot be in the past")
            status = "scheduled"
            scheduled_start_time = bot.scheduled_start_time
            print(f"\033[92m✅ [SERVICE] Scheduled join - time: {scheduled_start_time}\033[0m")
        else:
            # No scheduled time set and not immediate - default to immediate
            status = "pending"
            scheduled_start_time = None
            print(f"\033[92m✅ [SERVICE] No scheduled time - defaulting to immediate\033[0m")

    # 7. MeetingBot status update (pending or scheduled)
    print(f"\033[93m📋 [SERVICE] Updating bot status to: {status}\033[0m")
    bot.status = status
    bot.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(bot)
    print(f"\033[92m✅ [SERVICE] Bot status updated\033[0m")

    # 8. Celery task queuing with proper parameters
    print(f"\033[93m📋 [SERVICE] Queuing Celery task\033[0m")
    from app.jobs.celery_worker import celery_app
    from app.core.config import settings

    # Queue the Celery task with all required parameters
    task = celery_app.send_task("app.jobs.tasks.schedule_meeting_bot_task", args=[str(meeting_id), str(user_id), bearer_token, meeting_url], kwargs={"webhook_url": settings.BOT_WEBHOOK_URL})

    print(f"\033[92m✅ [SERVICE] Celery task queued - task_id: {task.id}\033[0m")

    # 9. Return task info dictionary
    return {
        "task_id": task.id,
        "bot_id": str(bot.id),
        "meeting_id": str(meeting_id),
        "status": status,
        "scheduled_start_time": scheduled_start_time,
        "created_at": bot.created_at,
    }
