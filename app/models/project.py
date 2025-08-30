import uuid
from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy import Column, String, Text, Boolean, DateTime

from .base import BaseDatabaseModel


class Project(BaseDatabaseModel, table=True):
    """Project model"""

    __tablename__ = "projects"

    name: str = Field(sa_column=Column(String, nullable=False))
    description: Optional[str] = Field(default=None, sa_column=Column(Text))
    is_archived: bool = Field(default=False, sa_column=Column(Boolean))
    created_by: uuid.UUID = Field(foreign_key="users.id", nullable=False)

    # Relationships
    created_by_user: "User" = Relationship(back_populates="created_projects")
    users: list["UserProject"] = Relationship(back_populates="project")
    meetings: list["ProjectMeeting"] = Relationship(back_populates="project")
    files: list["File"] = Relationship(back_populates="project")
    tasks: list["TaskProject"] = Relationship(back_populates="project")
    integrations: list["Integration"] = Relationship(back_populates="project")


class UserProject(SQLModel, table=True):
    """Junction table for users and projects (many-to-many relationship)"""

    __tablename__ = "users_projects"

    user_id: uuid.UUID = Field(foreign_key="users.id", primary_key=True)
    project_id: uuid.UUID = Field(foreign_key="projects.id", primary_key=True)
    role: str = Field(default="member", sa_column=Column(String))
    joined_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime(timezone=True)))

    # Relationships
    user: "User" = Relationship(back_populates="projects")
    project: Project = Relationship(back_populates="users")
