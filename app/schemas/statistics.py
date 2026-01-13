from datetime import date, datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


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
    count: int = Field(default=0, description="Primary count (e.g., tasks created, meetings held)")
    value: Optional[float] = Field(default=None, description="Secondary metric (e.g., completed count, duration)")


class TaskStatusBreakdown(BaseModel):
    """Detailed task status breakdown"""

    todo: int = Field(default=0, description="Tasks not yet started")
    in_progress: int = Field(default=0, description="Tasks currently being worked on")
    done: int = Field(default=0, description="Completed tasks")


class TaskStats(BaseModel):
    """Task statistics with trends"""

    total: int = Field(default=0, description="Total number of tasks")
    status_breakdown: TaskStatusBreakdown = Field(default_factory=TaskStatusBreakdown)
    overdue_count: int = Field(default=0, description="Number of overdue active tasks")
    completion_rate: float = Field(default=0.0, description="Percentage of completed tasks")
    due_today: int = Field(default=0, description="Tasks due today")
    due_this_week: int = Field(default=0, description="Tasks due within 7 days")
    created_this_period: int = Field(default=0, description="Tasks created in the selected period")
    completed_this_period: int = Field(default=0, description="Tasks completed in the selected period")
    chart_data: List[ChartDataPoint] = Field(default_factory=list)


class MeetingStats(BaseModel):
    """Meeting statistics with trends"""

    total_count: int = Field(default=0, description="Total number of meetings")
    total_duration_minutes: int = Field(default=0, description="Total duration in minutes")
    average_duration_minutes: float = Field(default=0.0, description="Average meeting duration")
    bot_usage_count: int = Field(default=0, description="Meetings with bot recordings")
    bot_usage_rate: float = Field(default=0.0, description="Percentage of meetings with bot")
    meetings_with_transcript: int = Field(default=0, description="Meetings that have transcripts")
    upcoming_count: int = Field(default=0, description="Upcoming scheduled meetings")
    chart_data: List[ChartDataPoint] = Field(default_factory=list)


class ProjectStats(BaseModel):
    """Project statistics"""

    total_count: int = Field(default=0, description="Total projects user is part of")
    active_count: int = Field(default=0, description="Active (non-archived) projects")
    archived_count: int = Field(default=0, description="Archived projects")
    owned_count: int = Field(default=0, description="Projects where user is owner/admin")
    member_count: int = Field(default=0, description="Projects where user is regular member")


class StorageStats(BaseModel):
    """Storage usage statistics"""

    total_files: int = Field(default=0, description="Total number of files")
    total_size_bytes: int = Field(default=0, description="Total storage in bytes")
    total_size_mb: float = Field(default=0.0, description="Total storage in megabytes")
    files_by_type: dict = Field(default_factory=dict, description="File count grouped by MIME type")


class QuickAccessMeeting(BaseModel):
    """Meeting for quick access panel"""

    id: UUID
    title: Optional[str] = None
    start_time: Optional[datetime] = None
    url: Optional[str] = None
    project_names: List[str] = Field(default_factory=list, description="Associated project names")
    status: str = "active"
    has_transcript: bool = False
    has_recording: bool = False


class QuickAccessTask(BaseModel):
    """Task for quick access panel"""

    id: UUID
    title: str
    due_date: Optional[datetime] = None
    priority: str = "medium"
    status: str = "todo"
    project_names: List[str] = Field(default_factory=list, description="Associated project names")
    is_overdue: bool = False


class QuickAccessProject(BaseModel):
    """Project for quick access panel"""

    id: UUID
    name: str
    description: Optional[str] = None
    role: str
    member_count: int = 0
    task_count: int = Field(default=0, description="Number of active tasks")
    meeting_count: int = Field(default=0, description="Number of meetings")
    joined_at: datetime


class QuickAccessData(BaseModel):
    """Quick access data for dashboard"""

    upcoming_meetings: List[QuickAccessMeeting] = Field(default_factory=list)
    recent_meetings: List[QuickAccessMeeting] = Field(default_factory=list)
    priority_tasks: List[QuickAccessTask] = Field(default_factory=list)
    active_projects: List[QuickAccessProject] = Field(default_factory=list)


class SummaryStats(BaseModel):
    """High-level summary statistics"""

    total_tasks: int = Field(default=0)
    total_meetings: int = Field(default=0)
    total_projects: int = Field(default=0)
    pending_tasks: int = Field(default=0, description="Tasks that need attention (overdue + due soon)")
    upcoming_meetings_24h: int = Field(default=0, description="Meetings in the next 24 hours")


class DashboardResponse(BaseModel):
    """Complete dashboard response"""

    period: DashboardPeriod
    scope: DashboardScope
    summary: SummaryStats = Field(default_factory=SummaryStats)
    tasks: TaskStats = Field(default_factory=TaskStats)
    meetings: MeetingStats = Field(default_factory=MeetingStats)
    projects: ProjectStats = Field(default_factory=ProjectStats)
    storage: StorageStats = Field(default_factory=StorageStats)
    quick_access: QuickAccessData = Field(default_factory=QuickAccessData)
