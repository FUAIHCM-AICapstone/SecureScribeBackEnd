from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, func
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from . import (
        File,
        Project,
        ProjectMeeting,
        TaskProject,
        User,
        UserProject,
    )


class Project(SQLModel, table=True):
    """Project model"""

    __tablename__ = "projects"

    id: int = Field(
        sa_column=Column(Integer, primary_key=True, autoincrement=True),
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
    )
    updated_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True), onupdate=func.now()))

    name: str = Field(sa_column=Column(String(255), nullable=False))
    description: Optional[str] = Field(default=None, sa_column=Column(Text))
    is_archived: bool = Field(default=False, sa_column=Column(Boolean))
    created_by: int = Field(foreign_key="users.id", nullable=False)

    # Relationships
    created_by_user: "User" = Relationship(
        back_populates="created_projects",
        sa_relationship_kwargs={"foreign_keys": "Project.created_by"},
    )  # type: ignore
    users: list["UserProject"] = Relationship(back_populates="project")
    meetings: list["ProjectMeeting"] = Relationship(back_populates="project")  # type: ignore
    files: list["File"] = Relationship(back_populates="project")  # type: ignore
    tasks: list["TaskProject"] = Relationship(back_populates="project")  # type: ignore


class UserProject(SQLModel, table=True):
    """Junction table for users and projects (many-to-many relationship)"""

    __tablename__ = "users_projects"

    user_id: int = Field(foreign_key="users.id", primary_key=True)
    project_id: int = Field(foreign_key="projects.id", primary_key=True)
    role: str = Field(default="member", sa_column=Column(String(50)))
    joined_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime(timezone=True)))

    # Relationships
    user: "User" = Relationship(
        back_populates="projects",
        sa_relationship_kwargs={"foreign_keys": "UserProject.user_id"},
    )  # type: ignore
    project: Project = Relationship(
        back_populates="users",
        sa_relationship_kwargs={"foreign_keys": "UserProject.project_id"},
    )
