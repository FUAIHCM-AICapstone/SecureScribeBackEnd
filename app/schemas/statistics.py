from datetime import date, datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


class DashboardPeriod(str, Enum):
    SEVEN_DAYS = "7d"
    THIRTY_DAYS = "30d"
    NINETY_DAYS = "90d"
    ALL_TIME = "all"


class DashboardScope(str, Enum):
    PERSONAL = "personal"
    PROJECT = "project"
    HYBRID = "hybrid"


class ChartDataPoint(BaseModel):
    date: date
    count: int
    value: Optional[float] = None  # For duration or other metrics


class TaskStats(BaseModel):
    total_assigned: int
    todo_count: int
    in_progress_count: int
    done_count: int
    overdue_count: int
    completion_rate: float
    chart_data: List[ChartDataPoint]


class MeetingStats(BaseModel):
    total_count: int
    total_duration_minutes: int
    average_duration_minutes: float
    bot_usage_count: int
    chart_data: List[ChartDataPoint]


class ProjectStats(BaseModel):
    total_active: int
    total_archived: int
    role_admin_count: int
    role_member_count: int


class StorageStats(BaseModel):
    total_files: int
    total_size_bytes: int
    total_size_mb: float


class QuickAccessMeeting(BaseModel):
    id: UUID
    title: Optional[str]
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    url: Optional[str]
    project_name: Optional[str]
    status: str
    has_transcript: bool


class QuickAccessTask(BaseModel):
    id: UUID
    title: str
    due_date: Optional[datetime]
    priority: str
    status: str
    project_name: Optional[str]


class QuickAccessProject(BaseModel):
    id: UUID
    name: str
    role: str
    member_count: int
    joined_at: datetime


class QuickAccessData(BaseModel):
    upcoming_meetings: List[QuickAccessMeeting]
    recent_meetings: List[QuickAccessMeeting]
    priority_tasks: List[QuickAccessTask]
    active_projects: List[QuickAccessProject]


class DashboardResponse(BaseModel):
    period: DashboardPeriod
    scope: DashboardScope
    tasks: TaskStats
    meetings: MeetingStats
    projects: ProjectStats
    storage: StorageStats
    quick_access: QuickAccessData
    chart_data: List[ChartDataPoint]
