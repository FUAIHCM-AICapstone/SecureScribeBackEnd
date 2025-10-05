from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel

from .common import ApiResponse, PaginatedResponse


class TagCreate(BaseModel):
    name: str
    scope: str = "global"


class TagUpdate(BaseModel):
    name: Optional[str] = None
    scope: Optional[str] = None
    is_deleted: Optional[bool] = None


class TagResponse(BaseModel):
    id: UUID
    name: str
    scope: str
    created_by: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None
    meeting_count: int = 0

    class Config:
        from_attributes = True


class TagFilter(BaseModel):
    name: Optional[str] = None
    scope: Optional[str] = None
    created_by: Optional[UUID] = None
    project_id: Optional[UUID] = None
    min_usage_count: Optional[int] = None
    max_usage_count: Optional[int] = None


class TagWithStats(TagResponse):
    pass


class TagBulkCreate(BaseModel):
    tags: List[TagCreate]


class TagBulkUpdate(BaseModel):
    updates: List[dict]


class TagBulkDelete(BaseModel):
    tag_ids: List[UUID]


TagApiResponse = ApiResponse[TagResponse]
TagsPaginatedResponse = PaginatedResponse[TagResponse]
TagStatsResponse = ApiResponse[dict]
