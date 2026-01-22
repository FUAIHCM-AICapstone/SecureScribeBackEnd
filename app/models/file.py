from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, Column, DateTime, Integer, String, Text, func
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from . import File, Meeting, Project, User


class File(SQLModel, table=True):
    """File model"""

    __tablename__ = "files"

    id: int = Field(
        sa_column=Column(Integer, primary_key=True, autoincrement=True),
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
    )
    updated_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True), onupdate=func.now()))

    filename: Optional[str] = Field(default=None, sa_column=Column(String(500)))
    mime_type: Optional[str] = Field(default=None, sa_column=Column(String(100)))
    size_bytes: Optional[int] = Field(default=None, sa_column=Column(BigInteger))
    storage_url: Optional[str] = Field(default=None, sa_column=Column(String(500)))
    file_type: Optional[str] = Field(default=None, sa_column=Column(String(50)))
    project_id: Optional[int] = Field(default=None, foreign_key="projects.id")
    meeting_id: Optional[int] = Field(default=None, foreign_key="meetings.id")
    uploaded_by: Optional[int] = Field(default=None, foreign_key="users.id")
    extracted_text: Optional[str] = Field(default=None, sa_column=Column(Text))
    qdrant_vector_id: Optional[str] = Field(default=None, sa_column=Column(String(255)))

    # Relationships
    project: Optional["Project"] = Relationship(back_populates="files")  # type: ignore
    meeting: Optional["Meeting"] = Relationship(back_populates="files")  # type: ignore
    uploaded_by_user: Optional["User"] = Relationship(
        back_populates="uploaded_files",
        sa_relationship_kwargs={"foreign_keys": "File.uploaded_by"},
    )
