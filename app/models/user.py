import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import Boolean, Column, DateTime, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSON
from sqlmodel import Field, Relationship

from .base import BaseDatabaseModel


class User(BaseDatabaseModel, table=True):
    """User model"""

    __tablename__ = "users"

    email: str = Field(sa_column=Column(String, unique=True, nullable=False))
    name: Optional[str] = Field(default=None, sa_column=Column(String))
    avatar_url: Optional[str] = Field(default=None, sa_column=Column(String))
    bio: Optional[str] = Field(default=None, sa_column=Column(Text))
    position: Optional[str] = Field(default=None, sa_column=Column(String))
    password_hash: Optional[str] = Field(default=None, sa_column=Column(String))

    # Relationships
    identities: list["UserIdentity"] = Relationship(back_populates="user")
    devices: list["UserDevice"] = Relationship(back_populates="user")
    projects: list["UserProject"] = Relationship(back_populates="user")  # type: ignore
    created_projects: list["Project"] = Relationship(back_populates="created_by_user")  # type: ignore
    created_meetings: list["Meeting"] = Relationship(back_populates="created_by_user")  # type: ignore
    uploaded_files: list["File"] = Relationship(back_populates="uploaded_by_user")  # type: ignore
    owned_files: list["File"] = Relationship(back_populates="owner_user")  # type: ignore
    created_tags: list["Tag"] = Relationship(back_populates="created_by_user")  # type: ignore
    created_tasks: list["Task"] = Relationship(back_populates="creator")  # type: ignore
    assigned_tasks: list["Task"] = Relationship(back_populates="assignee")  # type: ignore
    notifications: list["Notification"] = Relationship(back_populates="user")  # type: ignore
    audit_logs: list["AuditLog"] = Relationship(back_populates="actor_user")  # type: ignore
    edited_notes: list["MeetingNote"] = Relationship(back_populates="last_editor")  # type: ignore
    created_bots: list["MeetingBot"] = Relationship(back_populates="created_by_user")  # type: ignore


class UserIdentity(BaseDatabaseModel, table=True):
    """User identity for OAuth providers"""

    __tablename__ = "user_identities"

    user_id: uuid.UUID = Field(foreign_key="users.id", nullable=False)
    provider: str = Field(sa_column=Column(String, nullable=False))
    provider_user_id: str = Field(sa_column=Column(String, nullable=False))
    provider_email: Optional[str] = Field(default=None, sa_column=Column(String))
    provider_profile: Optional[Dict[str, Any]] = Field(
        default=None, sa_column=Column(JSON)
    )
    tenant_id: Optional[str] = Field(default=None, sa_column=Column(String))

    # Relationships
    user: User = Relationship(back_populates="identities")

    # Constraints
    __table_args__ = (
        UniqueConstraint("provider", "provider_user_id", name="unique_provider_user"),
    )


class UserDevice(BaseDatabaseModel, table=True):
    """User device for push notifications"""

    __tablename__ = "user_devices"

    user_id: uuid.UUID = Field(foreign_key="users.id", nullable=False)
    device_name: Optional[str] = Field(default=None, sa_column=Column(String))
    device_type: Optional[str] = Field(default=None, sa_column=Column(String))
    fcm_token: str = Field(sa_column=Column(Text, nullable=False))
    last_active_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )
    is_active: bool = Field(default=True, sa_column=Column(Boolean))

    # Relationships
    user: User = Relationship(back_populates="devices")
