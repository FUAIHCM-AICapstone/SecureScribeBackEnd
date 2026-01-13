import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session, joinedload

from app.models.meeting import Meeting, MeetingBot, MeetingBotLog, ProjectMeeting
from app.models.project import UserProject


def crud_create_meeting_bot(db: Session, meeting_id: uuid.UUID, scheduled_start_time: Optional[datetime], meeting_url: Optional[str], created_by: uuid.UUID, bot_id: Optional[uuid.UUID] = None, status: str = "active") -> MeetingBot:
    bot = MeetingBot(id=bot_id or uuid.uuid4(), meeting_id=meeting_id, scheduled_start_time=scheduled_start_time, meeting_url=meeting_url, created_by=created_by, status=status)
    db.add(bot)
    db.commit()
    db.refresh(bot)
    return bot


def crud_get_meeting_bot(db: Session, bot_id: uuid.UUID, include_relations: bool = True) -> Optional[MeetingBot]:
    if include_relations:
        return db.query(MeetingBot).options(joinedload(MeetingBot.logs), joinedload(MeetingBot.meeting).joinedload(Meeting.projects).joinedload(ProjectMeeting.project), joinedload(MeetingBot.meeting).joinedload(Meeting.created_by_user)).filter(MeetingBot.id == bot_id).first()
    return db.query(MeetingBot).filter(MeetingBot.id == bot_id).first()


def crud_get_meeting_bot_by_meeting(db: Session, meeting_id: uuid.UUID) -> Optional[MeetingBot]:
    return db.query(MeetingBot).filter(MeetingBot.meeting_id == meeting_id).first()


def crud_get_meeting_bots(db: Session, user_id: uuid.UUID, page: int = 1, limit: int = 20) -> Tuple[List[MeetingBot], int]:
    offset = (page - 1) * limit
    query = db.query(MeetingBot).options(joinedload(MeetingBot.logs), joinedload(MeetingBot.meeting).joinedload(Meeting.projects).joinedload(ProjectMeeting.project), joinedload(MeetingBot.meeting).joinedload(Meeting.created_by_user)).filter(MeetingBot.created_by == user_id).order_by(MeetingBot.created_at.desc())
    total = query.count()
    bots = query.offset(offset).limit(limit).all()
    return bots, total


def crud_update_meeting_bot(db: Session, bot_id: uuid.UUID, **updates) -> Optional[MeetingBot]:
    bot = db.query(MeetingBot).filter(MeetingBot.id == bot_id).first()
    if not bot:
        return None
    for key, value in updates.items():
        if hasattr(bot, key):
            setattr(bot, key, value)
    bot.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(bot)
    return bot


def crud_delete_meeting_bot(db: Session, bot_id: uuid.UUID) -> bool:
    bot = db.query(MeetingBot).filter(MeetingBot.id == bot_id).first()
    if not bot:
        return False
    db.query(MeetingBotLog).filter(MeetingBotLog.meeting_bot_id == bot_id).delete()
    db.delete(bot)
    db.commit()
    return True


def crud_create_bot_log(db: Session, bot_id: uuid.UUID, action: str, message: Optional[str] = None) -> MeetingBotLog:
    log = MeetingBotLog(meeting_bot_id=bot_id, action=action, message=message)
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def crud_get_bot_logs(db: Session, bot_id: uuid.UUID, page: int = 1, limit: int = 50) -> Tuple[List[MeetingBotLog], int]:
    offset = (page - 1) * limit
    query = db.query(MeetingBotLog).filter(MeetingBotLog.meeting_bot_id == bot_id).order_by(MeetingBotLog.created_at.desc())
    total = query.count()
    logs = query.offset(offset).limit(limit).all()
    return logs, total


def crud_get_meeting(db: Session, meeting_id: uuid.UUID) -> Optional[Meeting]:
    return db.query(Meeting).filter(Meeting.id == meeting_id, Meeting.is_deleted == False).first()


def crud_get_meeting_projects(db: Session, meeting_id: uuid.UUID) -> List[uuid.UUID]:
    return [p[0] for p in db.query(ProjectMeeting.project_id).filter(ProjectMeeting.meeting_id == meeting_id).all()]


def crud_check_user_project_access(db: Session, user_id: uuid.UUID, project_ids: List[uuid.UUID]) -> bool:
    if not project_ids:
        return False
    return db.query(UserProject).filter(UserProject.user_id == user_id, UserProject.project_id.in_(project_ids)).first() is not None
