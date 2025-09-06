import uuid
from typing import List, Optional

from pydantic import BaseModel

from app.schemas.common import ApiResponse, PaginatedResponse


class FileBase(BaseModel):
    filename: Optional[str] = None
    mime_type: Optional[str] = None
    size_bytes: Optional[int] = None
    file_type: Optional[str] = None
    project_id: Optional[uuid.UUID] = None
    meeting_id: Optional[uuid.UUID] = None


class FileCreate(FileBase):
    pass


class FileUpdate(BaseModel):
    filename: Optional[str] = None
    file_type: Optional[str] = None


class FileResponse(FileBase):
    id: uuid.UUID
    storage_url: Optional[str] = None
    uploaded_by: Optional[uuid.UUID] = None
    extracted_text: Optional[str] = None
    created_at: str
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class FileWithProject(FileResponse):
    project_name: Optional[str] = None
    can_access: bool = True


class FileWithMeeting(FileResponse):
    meeting_title: Optional[str] = None
    can_access: bool = True


class FileFilter(BaseModel):
    filename: Optional[str] = None
    mime_type: Optional[str] = None
    file_type: Optional[str] = None
    project_id: Optional[uuid.UUID] = None
    meeting_id: Optional[uuid.UUID] = None
    uploaded_by: Optional[uuid.UUID] = None


class BulkFileOperation(BaseModel):
    file_ids: List[uuid.UUID]
    operation: str  # "delete" or "move"
    target_project_id: Optional[uuid.UUID] = None
    target_meeting_id: Optional[uuid.UUID] = None


class BulkFileResponse(BaseModel):
    success: bool
    message: str
    data: List[dict]
    total_processed: int
    total_success: int
    total_failed: int


class FileApiResponse(ApiResponse[FileResponse]):
    pass


class FileWithProjectApiResponse(ApiResponse[FileWithProject]):
    pass


class FileWithMeetingApiResponse(ApiResponse[FileWithMeeting]):
    pass


class FilesPaginatedResponse(PaginatedResponse[FileResponse]):
    pass


class FilesWithProjectPaginatedResponse(PaginatedResponse[FileWithProject]):
    pass


class FilesWithMeetingPaginatedResponse(PaginatedResponse[FileWithMeeting]):
    pass
