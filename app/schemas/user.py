from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr, field_validator


class FileResponse(BaseModel):
    id: int
    filename: Optional[str]
    mime_type: Optional[str]
    size_bytes: Optional[int]
    storage_url: Optional[str]
    file_type: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AudioFileResponse(BaseModel):
    id: int
    file_url: Optional[str]
    seq_order: Optional[int]
    duration_seconds: Optional[int]
    is_concatenated: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TagResponse(BaseModel):
    id: int
    name: str
    scope: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserDeviceResponse(BaseModel):
    id: int
    device_name: Optional[str]
    device_type: Optional[str]
    last_active_at: Optional[datetime]
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ProjectResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    is_archived: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserProjectResponse(BaseModel):
    project: ProjectResponse
    role: str
    joined_at: datetime

    class Config:
        from_attributes = True


class MeetingResponse(BaseModel):
    id: int
    title: Optional[str]
    description: Optional[str]
    url: Optional[str]
    start_time: Optional[datetime]
    is_personal: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TaskResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    status: str
    due_date: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AuditLogResponse(BaseModel):
    id: int
    action: Optional[str]
    target_type: Optional[str]
    target_id: Optional[str]
    audit_metadata: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MeetingNoteResponse(BaseModel):
    id: int
    meeting_id: int
    content: Optional[str]
    last_editor_id: Optional[int]
    last_edited_at: Optional[datetime]
    input_tokens: Optional[int]
    output_tokens: Optional[int]
    total_tokens: Optional[int]
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MeetingBotResponse(BaseModel):
    id: int
    status: str
    meeting_url: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserIdentityResponse(BaseModel):
    id: int
    provider: str
    provider_user_id: str
    provider_email: Optional[str]
    tenant_id: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    position: Optional[str] = None

    @field_validator("email")
    @classmethod
    def validate_email_ascii(cls, v: str) -> str:
        """Ensure email contains only ASCII characters"""
        try:
            v.encode("ascii")
        except UnicodeEncodeError:
            raise ValueError("Email must contain only ASCII characters")
        return v


class UserUpdate(BaseModel):
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    position: Optional[str] = None


class BulkUserCreate(BaseModel):
    users: List[UserCreate]


class BulkUserUpdateItem(BaseModel):
    id: int
    updates: UserUpdate


class BulkUserUpdate(BaseModel):
    users: List[BulkUserUpdateItem]


class BulkUserDelete(BaseModel):
    user_ids: List[int]


class BulkOperationResult(BaseModel):
    success: bool
    id: Optional[int] = None
    error: Optional[str] = None


class BulkUserResponse(BaseModel):
    success: bool
    message: str
    data: List[BulkOperationResult]
    total_processed: int
    total_success: int
    total_failed: int


class UserResponse(BaseModel):
    id: int
    email: str
    name: Optional[str]
    avatar_url: Optional[str]
    bio: Optional[str]
    position: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime] = None

    # Relationships
    # uploaded_files: List[FileResponse] = []
    # uploaded_audio_files: List[AudioFileResponse] = []
    # created_tags: List[TagResponse] = []
    # devices: List[UserDeviceResponse] = []
    # projects: List[UserProjectResponse] = []
    # created_projects: List[ProjectResponse] = []
    # created_meetings: List[MeetingResponse] = []
    # created_tasks: List[TaskResponse] = []
    # assigned_tasks: List[TaskResponse] = []
    # notifications: List[NotificationResponse] = []
    # audit_logs: List[AuditLogResponse] = []
    # edited_notes: List[MeetingNoteResponse] = []
    # created_bots: List[MeetingBotResponse] = []
    # identities: List[UserIdentityResponse] = []

    class Config:
        from_attributes = True


class DeviceFCMUpdate(BaseModel):
    device_name: str
    fcm_token: str
    device_type: Optional[str] = "web"
