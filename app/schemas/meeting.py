from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from .common import ApiResponse, PaginatedResponse


class ProjectResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    is_archived: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MeetingCreate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None
    start_time: Optional[datetime] = None
    is_personal: bool = False
    project_ids: List[UUID] = Field(default_factory=list)


class MeetingUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None
    start_time: Optional[datetime] = None
    status: Optional[str] = None


class MeetingFilter(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None
    start_time_gte: Optional[datetime] = None
    start_time_lte: Optional[datetime] = None
    status: Optional[str] = None
    is_personal: Optional[bool] = None
    created_by: Optional[UUID] = None
    project_id: Optional[UUID] = None
    tag_ids: List[UUID] = Field(default_factory=list)


class MeetingResponse(BaseModel):
    id: UUID
    title: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None
    start_time: Optional[datetime] = None
    created_by: UUID
    is_personal: bool
    status: str
    is_deleted: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    projects: List[ProjectResponse] = Field(default_factory=list)
    can_access: bool = True

    class Config:
        from_attributes = True


class MeetingWithProjects(MeetingResponse):
    project_count: int = 0
    member_count: int = 0


MeetingApiResponse = ApiResponse[MeetingResponse]
MeetingsPaginatedResponse = PaginatedResponse[MeetingResponse]
MeetingWithProjectsApiResponse = ApiResponse[MeetingWithProjects]
