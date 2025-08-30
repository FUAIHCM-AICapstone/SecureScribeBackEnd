import uuid
from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy import Column, String, Text, DateTime

from .base import BaseDatabaseModel


class Task(BaseDatabaseModel, table=True):
    """Task model"""

    __tablename__ = "tasks"

    title: str = Field(sa_column=Column(String, nullable=False))
    description: Optional[str] = Field(default=None, sa_column=Column(Text))
    creator_id: uuid.UUID = Field(foreign_key="users.id", nullable=False)
    assignee_id: Optional[uuid.UUID] = Field(default=None, foreign_key="users.id")
    status: str = Field(default="todo", sa_column=Column(String))
    meeting_id: Optional[uuid.UUID] = Field(default=None, foreign_key="meetings.id")
    due_date: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    reminder_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True)))

    # Relationships
    creator: "User" = Relationship(back_populates="created_tasks")
    assignee: Optional["User"] = Relationship(back_populates="assigned_tasks")
    meeting: Optional["Meeting"] = Relationship(back_populates="tasks")
    projects: list["TaskProject"] = Relationship(back_populates="task")


class TaskProject(SQLModel, table=True):
    """Junction table for tasks and projects (many-to-many relationship)"""

    __tablename__ = "tasks_projects"

    task_id: uuid.UUID = Field(foreign_key="tasks.id", primary_key=True)
    project_id: uuid.UUID = Field(foreign_key="projects.id", primary_key=True)

    # Relationships
    task: Task = Relationship(back_populates="projects")
    project: "Project" = Relationship(back_populates="tasks")
