from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from .common import ApiResponse, PaginatedResponse


# Base schemas
class ProjectBase(BaseModel):
    """Base project schema"""

    name: str = Field(..., min_length=1, max_length=255, description="Project name")
    description: Optional[str] = Field(None, description="Project description")

    @field_validator("name")
    @classmethod
    def validate_name_not_whitespace(cls, v):
        if isinstance(v, str) and v.strip() == "":
            raise ValueError("Project name cannot be only whitespace")
        return v.strip() if isinstance(v, str) else v


class ProjectCreate(ProjectBase):
    """Schema for creating a new project"""

    pass


class ProjectUpdate(BaseModel):
    """Schema for updating a project"""

    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Project name")
    description: Optional[str] = Field(None, description="Project description")
    is_archived: Optional[bool] = Field(None, description="Whether project is archived")


class ProjectResponse(ProjectBase):
    """Schema for project response"""

    id: UUID
    is_archived: bool
    created_by: UUID
    created_at: datetime
    updated_at: Optional[datetime]
    member_count: Optional[int] = Field(None, description="Number of project members")


class ProjectWithMembers(ProjectResponse):
    """Project response with full member details"""

    members: List["UserProjectResponse"] = Field(default_factory=list)


# User-Project relationship schemas
class UserProjectBase(BaseModel):
    """Base user-project relationship schema"""

    user_id: UUID
    project_id: UUID
    role: str = Field("member", description="User role in project")


class UserProjectCreate(BaseModel):
    """Schema for adding user to project"""

    user_id: UUID = Field(..., description="User ID to add to project")
    role: str = Field("member", description="Role to assign")


class UserProjectUpdate(BaseModel):
    """Schema for updating user role in project"""

    role: str = Field(..., description="New role for user")


class UserProjectResponse(BaseModel):
    """Schema for user-project relationship response"""

    user_id: UUID
    project_id: UUID
    role: str
    joined_at: datetime

    # Include user details
    user: Optional[dict] = Field(None, description="User details")


# Project member management schemas
class ProjectMembersResponse(BaseModel):
    """Response for project members list"""

    project_id: UUID
    members: List[UserProjectResponse]
    total_count: int


class BulkUserProjectCreate(BaseModel):
    """Schema for bulk adding users to project"""

    users: List[UserProjectCreate] = Field(..., description="List of users to add")


class BulkUserProjectResponse(BaseModel):
    """Response for bulk operations"""

    success: bool
    message: str
    data: List[dict]
    total_processed: int
    total_success: int
    total_failed: int


# Project query/filter schemas
class ProjectFilter(BaseModel):
    """Schema for project filtering"""

    name: Optional[str] = None
    is_archived: Optional[bool] = None
    created_by: Optional[UUID] = None
    member_id: Optional[UUID] = None  # Filter projects by member
    created_at_gte: Optional[str] = None
    created_at_lte: Optional[str] = None


# API Response types
ProjectApiResponse = ApiResponse[ProjectResponse]
ProjectWithMembersApiResponse = ApiResponse[ProjectWithMembers]
ProjectsPaginatedResponse = PaginatedResponse[ProjectResponse]
ProjectMembersApiResponse = ApiResponse[ProjectMembersResponse]
UserProjectApiResponse = ApiResponse[UserProjectResponse]


# Forward references resolution
ProjectWithMembers.model_rebuild()
