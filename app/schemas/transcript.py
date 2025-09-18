import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.schemas.common import ApiResponse


class TranscriptBase(BaseModel):
    meeting_id: uuid.UUID
    content: Optional[str] = None
    audio_concat_file_id: Optional[uuid.UUID] = None


class TranscriptCreate(TranscriptBase):
    pass


class TranscriptUpdate(BaseModel):
    content: Optional[str] = None
    extracted_text_for_search: Optional[str] = None
    qdrant_vector_id: Optional[str] = None


class TranscriptResponse(BaseModel):
    id: uuid.UUID
    meeting_id: uuid.UUID
    content: Optional[str]
    audio_concat_file_id: Optional[uuid.UUID]
    extracted_text_for_search: Optional[str]
    qdrant_vector_id: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TranscriptApiResponse(ApiResponse[TranscriptResponse]):
    pass
