import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


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