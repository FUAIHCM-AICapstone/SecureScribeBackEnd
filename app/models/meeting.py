import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from . import (
        AudioFile,
        File,
        Meeting,
        MeetingBot,
        MeetingBotLog,
        MeetingNote,
        MeetingTag,
        Project,
        ProjectMeeting,
        Task,
        Transcript,
        User,
    )


class Meeting(SQLModel, table=True):
    """Meeting model"""

    __tablename__ = "meetings"

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

    title: Optional[str] = Field(default=None, sa_column=Column(String))
    description: Optional[str] = Field(default=None, sa_column=Column(Text))
    url: Optional[str] = Field(default=None, sa_column=Column(String))
    start_time: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )
    created_by: uuid.UUID = Field(foreign_key="users.id", nullable=False)
    is_personal: bool = Field(default=False, sa_column=Column(Boolean))

    # Relationships
    created_by_user: "User" = Relationship(
        back_populates="created_meetings",
        sa_relationship_kwargs={"foreign_keys": "Meeting.created_by"},
    )  # type: ignore
    projects: list["ProjectMeeting"] = Relationship(back_populates="meeting")
    audio_files: list["AudioFile"] = Relationship(back_populates="meeting")
    transcript: Optional["Transcript"] = Relationship(back_populates="meeting")
    notes: Optional["MeetingNote"] = Relationship(back_populates="meeting")
    files: list["File"] = Relationship(back_populates="meeting")  # type: ignore
    tags: list["MeetingTag"] = Relationship(back_populates="meeting")  # type: ignore
    tasks: list["Task"] = Relationship(back_populates="meeting")  # type: ignore
    bot: Optional["MeetingBot"] = Relationship(back_populates="meeting")


class ProjectMeeting(SQLModel, table=True):
    """Junction table for projects and meetings (many-to-many relationship)"""

    __tablename__ = "projects_meetings"

    project_id: uuid.UUID = Field(foreign_key="projects.id", primary_key=True)
    meeting_id: uuid.UUID = Field(foreign_key="meetings.id", primary_key=True)

    # Relationships
    project: "Project" = Relationship(
        back_populates="meetings",
        sa_relationship_kwargs={"foreign_keys": "ProjectMeeting.project_id"},
    )  # type: ignore
    meeting: Meeting = Relationship(
        back_populates="projects",
        sa_relationship_kwargs={"foreign_keys": "ProjectMeeting.meeting_id"},
    )


class AudioFile(SQLModel, table=True):
    """Audio file model"""

    __tablename__ = "audio_files"

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

    meeting_id: uuid.UUID = Field(foreign_key="meetings.id", nullable=False)
    uploaded_by: uuid.UUID = Field(foreign_key="users.id", nullable=False)
    file_url: Optional[str] = Field(default=None, sa_column=Column(String))
    seq_order: Optional[int] = Field(default=None, sa_column=Column(Integer))
    duration_seconds: Optional[int] = Field(default=None, sa_column=Column(Integer))
    is_concatenated: bool = Field(default=False, sa_column=Column(Boolean))

    # Relationships
    meeting: Meeting = Relationship(back_populates="audio_files")
    uploaded_by_user: "User" = Relationship(
        back_populates="uploaded_audio_files",
        sa_relationship_kwargs={"foreign_keys": "AudioFile.uploaded_by"},
    )  # type: ignore
    transcript: Optional["Transcript"] = Relationship(
        back_populates="audio_concat_file",
        sa_relationship_kwargs={"foreign_keys": "Transcript.audio_concat_file_id"},
    )


class Transcript(SQLModel, table=True):
    """Transcript model"""

    __tablename__ = "transcripts"

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

    meeting_id: uuid.UUID = Field(
        foreign_key="meetings.id", unique=True, nullable=False
    )
    content: Optional[str] = Field(default=None, sa_column=Column(Text))
    audio_concat_file_id: Optional[uuid.UUID] = Field(
        default=None, foreign_key="audio_files.id"
    )
    extracted_text_for_search: Optional[str] = Field(
        default=None, sa_column=Column(Text)
    )
    qdrant_vector_id: Optional[str] = Field(default=None, sa_column=Column(String))

    # Relationships
    meeting: Meeting = Relationship(back_populates="transcript")
    audio_concat_file: Optional[AudioFile] = Relationship(
        back_populates="transcript",
        sa_relationship_kwargs={"foreign_keys": "Transcript.audio_concat_file_id"},
    )


class MeetingNote(SQLModel, table=True):
    """Meeting notes model"""

    __tablename__ = "meeting_notes"

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

    meeting_id: uuid.UUID = Field(
        foreign_key="meetings.id", unique=True, nullable=False
    )
    content: Optional[str] = Field(default=None, sa_column=Column(Text))
    last_editor_id: Optional[uuid.UUID] = Field(default=None, foreign_key="users.id")
    last_edited_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )

    # Relationships
    meeting: Meeting = Relationship(back_populates="notes")
    last_editor: Optional["User"] = Relationship(
        back_populates="edited_notes",
        sa_relationship_kwargs={"foreign_keys": "MeetingNote.last_editor_id"},
    )  # type: ignore


class MeetingBot(SQLModel, table=True):
    """Meeting bot model"""

    __tablename__ = "meeting_bots"

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

    meeting_id: uuid.UUID = Field(foreign_key="meetings.id", nullable=False)
    scheduled_start_time: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )
    actual_start_time: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )
    actual_end_time: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )
    status: str = Field(default="pending", sa_column=Column(String))
    meeting_url: Optional[str] = Field(default=None, sa_column=Column(String))
    retry_count: int = Field(default=0, sa_column=Column(Integer))
    last_error: Optional[str] = Field(default=None, sa_column=Column(Text))
    created_by: uuid.UUID = Field(foreign_key="users.id", nullable=False)

    # Relationships
    meeting: Meeting = Relationship(back_populates="bot")
    created_by_user: "User" = Relationship(
        back_populates="created_bots",
        sa_relationship_kwargs={"foreign_keys": "MeetingBot.created_by"},
    )  # type: ignore
    logs: list["MeetingBotLog"] = Relationship(back_populates="meeting_bot")


class MeetingBotLog(SQLModel, table=True):
    """Meeting bot logs model"""

    __tablename__ = "meeting_bot_logs"

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

    meeting_bot_id: uuid.UUID = Field(foreign_key="meeting_bots.id", nullable=False)
    action: Optional[str] = Field(default=None, sa_column=Column(String))
    message: Optional[str] = Field(default=None, sa_column=Column(Text))

    # Relationships
    meeting_bot: MeetingBot = Relationship(back_populates="logs")
