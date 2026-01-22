from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.schemas.common import ApiResponse


class AudioFileBase(BaseModel):
    meeting_id: int
    file_url: Optional[str] = None
    seq_order: Optional[int] = None
    duration_seconds: Optional[int] = None


class AudioFileCreate(AudioFileBase):
    uploaded_by: int


class AudioFileUpdate(BaseModel):
    seq_order: Optional[int] = None
    duration_seconds: Optional[int] = None


class AudioFileResponse(BaseModel):
    id: int
    meeting_id: int
    uploaded_by: int
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
