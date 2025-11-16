import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from app.schemas.project import ProjectResponse
from app.schemas.user import UserResponse


class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    assignee_id: Optional[uuid.UUID] = None
    meeting_id: Optional[uuid.UUID] = None
    project_ids: List[uuid.UUID] = []
    status: Optional[str] = "todo"
    priority: Optional[str] = "Trung bình"
    due_date: Optional[datetime] = None
    reminder_at: Optional[datetime] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    assignee_id: Optional[uuid.UUID] = None
    status: Optional[str] = None
    due_date: Optional[datetime] = None
    reminder_at: Optional[datetime] = None


class TaskResponse(BaseModel):
    id: uuid.UUID
    title: str
    description: Optional[str] = None
    status: str
    creator_id: uuid.UUID
    assignee_id: Optional[uuid.UUID] = None
    meeting_id: Optional[uuid.UUID] = None
    due_date: Optional[datetime] = None
    reminder_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    creator: Optional[UserResponse] = None
    assignee: Optional[UserResponse] = None
    projects: List[ProjectResponse] = []

    class Config:
        from_attributes = True


class BulkTaskCreate(BaseModel):
    tasks: List[TaskCreate]


class BulkTaskUpdateItem(BaseModel):
    id: uuid.UUID
    updates: TaskUpdate


class BulkTaskUpdate(BaseModel):
    tasks: List[BulkTaskUpdateItem]


class BulkTaskDelete(BaseModel):
    task_ids: List[uuid.UUID]


class BulkTaskResponse(BaseModel):
    success: bool
    message: str
    data: List[dict]
    total_processed: int
    total_success: int
    total_failed: int
