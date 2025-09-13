import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from app.schemas.common import ApiResponse

class AudioFileBase(BaseModel):
    meeting_id: uuid.UUID
    file_url: Optional[str] = None
    seq_order: Optional[int] = None
    duration_seconds: Optional[int] = None

class AudioFileCreate(AudioFileBase):
    uploaded_by: uuid.UUID

class AudioFileUpdate(BaseModel):
    seq_order: Optional[int] = None
    duration_seconds: Optional[int] = None

class AudioFileResponse(BaseModel):
    id: uuid.UUID
    meeting_id: uuid.UUID
    uploaded_by: uuid.UUID
    file_url: Optional[str]
    seq_order: Optional[int]
    duration_seconds: Optional[int]
    is_concatenated: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class AudioFileApiResponse(ApiResponse[AudioFileResponse]):
    pass