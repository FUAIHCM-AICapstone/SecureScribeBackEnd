import uuid
from datetime import datetime
from typing import List, Optional, Tuple

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from app.models.meeting import Meeting, MeetingBot, MeetingBotLog
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
    bot = (
        db.query(MeetingBot)
        .options(joinedload(MeetingBot.logs), joinedload(MeetingBot.meeting))
        .filter(MeetingBot.id == bot_id)
        .first()
    )
    return bot


def get_meeting_bot_by_meeting(db: Session, meeting_id: uuid.UUID, user_id: uuid.UUID) -> Optional[MeetingBot]:
    """Get meeting bot by meeting ID"""
    bot = (
        db.query(MeetingBot)
        .options(joinedload(MeetingBot.logs))
        .filter(MeetingBot.meeting_id == meeting_id)
        .first()
    )
    return bot


def get_meeting_bots(db: Session, user_id: uuid.UUID, page: int = 1, limit: int = 20) -> Tuple[List[MeetingBot], int]:
    """Get meeting bots with pagination"""
    offset = (page - 1) * limit
    
    query = (
        db.query(MeetingBot)
        .options(joinedload(MeetingBot.logs), joinedload(MeetingBot.meeting))
        .filter(MeetingBot.created_by == user_id)
    )
    
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