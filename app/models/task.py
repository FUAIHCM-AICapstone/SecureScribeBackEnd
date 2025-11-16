import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Column, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from . import Meeting, Project, Task, TaskProject, User


class Task(SQLModel, table=True):
    """Task model"""

    __tablename__ = "tasks"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
    )
    updated_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True), onupdate=func.now()))

    title: str = Field(sa_column=Column(String, nullable=False))
    description: Optional[str] = Field(default=None, sa_column=Column(Text))
    creator_id: uuid.UUID = Field(foreign_key="users.id", nullable=False)
    assignee_id: Optional[uuid.UUID] = Field(default=None, foreign_key="users.id")
    status: str = Field(default="todo", sa_column=Column(String))
    priority: str = Field(default="Trung bình", sa_column=Column(String))
    meeting_id: Optional[uuid.UUID] = Field(default=None, foreign_key="meetings.id")
    due_date: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    reminder_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True)))

    # Relationships
    creator: "User" = Relationship(
        back_populates="created_tasks",
        sa_relationship_kwargs={"foreign_keys": "Task.creator_id"},
    )  # type: ignore
    assignee: Optional["User"] = Relationship(
        back_populates="assigned_tasks",
        sa_relationship_kwargs={"foreign_keys": "Task.assignee_id"},
    )  # type: ignore
    meeting: Optional["Meeting"] = Relationship(back_populates="tasks")  # type: ignore
    projects: list["TaskProject"] = Relationship(back_populates="task")


class TaskProject(SQLModel, table=True):
    """Junction table for tasks and projects (many-to-many relationship)"""

    __tablename__ = "tasks_projects"

    task_id: uuid.UUID = Field(foreign_key="tasks.id", primary_key=True)
    project_id: uuid.UUID = Field(foreign_key="projects.id", primary_key=True)

    # Relationships
    task: "Task" = Relationship(
        back_populates="projects",
        sa_relationship_kwargs={"foreign_keys": "TaskProject.task_id"},
    )
    project: "Project" = Relationship(
        back_populates="tasks",
        sa_relationship_kwargs={"foreign_keys": "TaskProject.project_id"},
    )  # type: ignore
