import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional

from sqlalchemy import Boolean, Column, DateTime, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from . import (
        AudioFile,
        AuditLog,
        File,
        Meeting,
        MeetingBot,
        MeetingNote,
        Notification,
        Project,
        Tag,
        Task,
        User,
        UserProject,
    )


class User(SQLModel, table=True):
    """User model"""

    __tablename__ = "users"

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

    email: str = Field(sa_column=Column(String, unique=True, nullable=False))
    name: Optional[str] = Field(default=None, sa_column=Column(String))
    avatar_url: Optional[str] = Field(default=None, sa_column=Column(String))
    bio: Optional[str] = Field(default=None, sa_column=Column(Text))
    position: Optional[str] = Field(default=None, sa_column=Column(String))

    # Relationships
    identities: list["UserIdentity"] = Relationship(back_populates="user")
    devices: list["UserDevice"] = Relationship(back_populates="user")
    projects: list["UserProject"] = Relationship(back_populates="user")  # type: ignore
    created_projects: list["Project"] = Relationship(back_populates="created_by_user")  # type: ignore
    created_meetings: list["Meeting"] = Relationship(back_populates="created_by_user")  # type: ignore
    uploaded_files: list["File"] = Relationship(
        back_populates="uploaded_by_user",
        sa_relationship_kwargs={"foreign_keys": "File.uploaded_by"},
    )  # type: ignore
    uploaded_audio_files: list["AudioFile"] = Relationship(
        back_populates="uploaded_by_user",
        sa_relationship_kwargs={"foreign_keys": "AudioFile.uploaded_by"},
    )  # type: ignore
    created_tags: list["Tag"] = Relationship(back_populates="created_by_user")  # type: ignore
    created_tasks: list["Task"] = Relationship(
        back_populates="creator",
        sa_relationship_kwargs={"foreign_keys": "Task.creator_id"},
    )  # type: ignore
    assigned_tasks: list["Task"] = Relationship(
        back_populates="assignee",
        sa_relationship_kwargs={"foreign_keys": "Task.assignee_id"},
    )  # type: ignore
    notifications: list["Notification"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"foreign_keys": "Notification.user_id"},
    )  # type: ignore
    audit_logs: list["AuditLog"] = Relationship(
        back_populates="actor_user",
        sa_relationship_kwargs={"foreign_keys": "AuditLog.actor_user_id"},
    )  # type: ignore
    edited_notes: list["MeetingNote"] = Relationship(
        back_populates="last_editor",
        sa_relationship_kwargs={"foreign_keys": "MeetingNote.last_editor_id"},
    )  # type: ignore
    created_bots: list["MeetingBot"] = Relationship(
        back_populates="created_by_user",
        sa_relationship_kwargs={"foreign_keys": "MeetingBot.created_by"},
    )  # type: ignore


class UserIdentity(SQLModel, table=True):
    """User identity for OAuth providers"""

    __tablename__ = "user_identities"

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

    user_id: uuid.UUID = Field(foreign_key="users.id", nullable=False)
    provider: str = Field(sa_column=Column(String, nullable=False))
    provider_user_id: str = Field(sa_column=Column(String, nullable=False))
    provider_email: Optional[str] = Field(default=None, sa_column=Column(String))
    provider_profile: Optional[Dict[str, Any]] = Field(
        default=None, sa_column=Column(JSON)
    )
    tenant_id: Optional[str] = Field(default=None, sa_column=Column(String))

    # Relationships
    user: User = Relationship(
        back_populates="identities",
        sa_relationship_kwargs={"foreign_keys": "UserIdentity.user_id"},
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint("provider", "provider_user_id", name="unique_provider_user"),
    )


class UserDevice(SQLModel, table=True):
    """User device for push notifications"""

    __tablename__ = "user_devices"

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

    user_id: uuid.UUID = Field(foreign_key="users.id", nullable=False)
    device_name: Optional[str] = Field(default=None, sa_column=Column(String))
    device_type: Optional[str] = Field(default=None, sa_column=Column(String))
    fcm_token: str = Field(sa_column=Column(Text, nullable=False))
    last_active_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )
    is_active: bool = Field(default=True, sa_column=Column(Boolean))

    # Relationships
    user: User = Relationship(
        back_populates="devices",
        sa_relationship_kwargs={"foreign_keys": "UserDevice.user_id"},
    )
