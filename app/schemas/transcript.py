from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from app.schemas.common import ApiResponse, PaginatedResponse


class TranscriptBase(BaseModel):
    meeting_id: int
    content: Optional[str] = None
    audio_concat_file_id: Optional[int] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_tokens: Optional[int] = None


class TranscriptCreate(TranscriptBase):
    pass


class TranscriptUpdate(BaseModel):
    content: Optional[str] = None
    extracted_text_for_search: Optional[str] = None
    qdrant_vector_id: Optional[str] = None


class TranscriptResponse(BaseModel):
    id: int
    meeting_id: int
    content: Optional[str]
    audio_concat_file_id: Optional[int]
    extracted_text_for_search: Optional[str]
    qdrant_vector_id: Optional[str]
    input_tokens: Optional[int]
    output_tokens: Optional[int]
    total_tokens: Optional[int]
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TranscriptApiResponse(ApiResponse[TranscriptResponse]):
    pass


class TranscriptsPaginatedResponse(PaginatedResponse[TranscriptResponse]):
    pass


class BulkTranscriptCreate(BaseModel):
    transcripts: List[TranscriptCreate]


class BulkTranscriptUpdateItem(BaseModel):
    id: int
    updates: TranscriptUpdate


class BulkTranscriptUpdate(BaseModel):
    transcripts: List[BulkTranscriptUpdateItem]


class BulkTranscriptDelete(BaseModel):
    transcript_ids: List[int]


class BulkTranscriptResponse(BaseModel):
    success: bool
    message: str
    data: List[dict]
    total_processed: int
    total_success: int
    total_failed: int


class TranscriptReindexResponse(ApiResponse[dict]):
    pass
