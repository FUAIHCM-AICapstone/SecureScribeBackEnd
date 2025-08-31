import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, Column, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from . import (
        File,
        Integration,
        Project,
        ProjectMeeting,
        TaskProject,
        User,
        UserProject,
    )


class Project(SQLModel, table=True):
    """Project model"""

    __tablename__ = "projects"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(
            DateTime(timezone=True), server_default=func.now(), nullable=False
        ),
    )
    updated_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True), onupdate=func.now())
    )

    name: str = Field(sa_column=Column(String, nullable=False))
    description: Optional[str] = Field(default=None, sa_column=Column(Text))
    is_archived: bool = Field(default=False, sa_column=Column(Boolean))
    created_by: uuid.UUID = Field(foreign_key="users.id", nullable=False)

    # Relationships
    created_by_user: "User" = Relationship(
        back_populates="created_projects",
        sa_relationship_kwargs={"foreign_keys": "Project.created_by"},
    )  # type: ignore
    users: list["UserProject"] = Relationship(back_populates="project")
    meetings: list["ProjectMeeting"] = Relationship(back_populates="project")  # type: ignore
    files: list["File"] = Relationship(back_populates="project")  # type: ignore
    tasks: list["TaskProject"] = Relationship(back_populates="project")  # type: ignore
    integrations: list["Integration"] = Relationship(back_populates="project")  # type: ignore


class UserProject(SQLModel, table=True):
    """Junction table for users and projects (many-to-many relationship)"""

    __tablename__ = "users_projects"

    user_id: uuid.UUID = Field(foreign_key="users.id", primary_key=True)
    project_id: uuid.UUID = Field(foreign_key="projects.id", primary_key=True)
    role: str = Field(default="member", sa_column=Column(String))
    joined_at: datetime = Field(
        default_factory=datetime.utcnow, sa_column=Column(DateTime(timezone=True))
    )

    # Relationships
    user: "User" = Relationship(
        back_populates="projects",
        sa_relationship_kwargs={"foreign_keys": "UserProject.user_id"},
    )  # type: ignore
    project: Project = Relationship(
        back_populates="users",
        sa_relationship_kwargs={"foreign_keys": "UserProject.project_id"},
    )
