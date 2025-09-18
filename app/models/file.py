import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, Column, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from . import File, Meeting, Project, User


class File(SQLModel, table=True):
    """File model"""

    __tablename__ = "files"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
    )
    updated_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True), onupdate=func.now()))

    filename: Optional[str] = Field(default=None, sa_column=Column(String))
    mime_type: Optional[str] = Field(default=None, sa_column=Column(String))
    size_bytes: Optional[int] = Field(default=None, sa_column=Column(BigInteger))
    storage_url: Optional[str] = Field(default=None, sa_column=Column(String))
    file_type: Optional[str] = Field(default=None, sa_column=Column(String))
    project_id: Optional[uuid.UUID] = Field(default=None, foreign_key="projects.id")
    meeting_id: Optional[uuid.UUID] = Field(default=None, foreign_key="meetings.id")
    uploaded_by: Optional[uuid.UUID] = Field(default=None, foreign_key="users.id")
    extracted_text: Optional[str] = Field(default=None, sa_column=Column(Text))
    qdrant_vector_id: Optional[str] = Field(default=None, sa_column=Column(String))

    # Relationships
    project: Optional["Project"] = Relationship(back_populates="files")  # type: ignore
    meeting: Optional["Meeting"] = Relationship(back_populates="files")  # type: ignore
    uploaded_by_user: Optional["User"] = Relationship(
        back_populates="uploaded_files",
        sa_relationship_kwargs={"foreign_keys": "File.uploaded_by"},
    )
