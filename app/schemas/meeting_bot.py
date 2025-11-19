import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, field_validator


class MeetingBotCreate(BaseModel):
    meeting_id: uuid.UUID
    scheduled_start_time: Optional[datetime] = None
    meeting_url: Optional[str] = None


class MeetingBotUpdate(BaseModel):
    scheduled_start_time: Optional[datetime] = None
    actual_start_time: Optional[datetime] = None
    actual_end_time: Optional[datetime] = None
    status: Optional[str] = None
    meeting_url: Optional[str] = None
    last_error: Optional[str] = None


class MeetingBotLogResponse(BaseModel):
    id: uuid.UUID
    action: Optional[str]
    message: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class MeetingBotResponse(BaseModel):
    id: uuid.UUID
    meeting_id: uuid.UUID
    scheduled_start_time: Optional[datetime]
    actual_start_time: Optional[datetime]
    actual_end_time: Optional[datetime]
    status: str
    meeting_url: Optional[str]
    retry_count: int
    last_error: Optional[str]
    created_by: uuid.UUID
    created_at: datetime
    updated_at: Optional[datetime]
    logs: List[MeetingBotLogResponse] = []

    class Config:
        from_attributes = True


class MeetingBotLogCreate(BaseModel):
    action: Optional[str] = None
    message: Optional[str] = None


class MeetingBotJoinRequest(BaseModel):
    """Request schema for triggering bot to join a meeting"""

    meeting_url: Optional[str] = None
    immediate: bool = False

    @field_validator("meeting_url")
    @classmethod
    def validate_meeting_url(cls, v: Optional[str]) -> Optional[str]:
        """Validate meeting_url max length"""
        if v is not None and len(v) > 2048:
            raise ValueError("meeting_url must not exceed 2048 characters")
        return v


class MeetingBotJoinResponse(BaseModel):
    """Response schema for bot join operation"""

    task_id: str
    bot_id: uuid.UUID
    meeting_id: uuid.UUID
    status: str
    scheduled_start_time: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class BotWebhookCallback(BaseModel):
    """Webhook callback schema from bot service"""

    botId: str
    meetingUrl: str
    status: str
    teamId: str
    timestamp: str
    userId: str
