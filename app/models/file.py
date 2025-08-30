import uuid
from typing import Optional

from sqlalchemy import BigInteger, Column, String, Text
from sqlmodel import Field, Relationship

from .base import BaseDatabaseModel


class File(BaseDatabaseModel, table=True):
    """File model"""

    __tablename__ = "files"

    filename: Optional[str] = Field(default=None, sa_column=Column(String))
    mime_type: Optional[str] = Field(default=None, sa_column=Column(String))
    size_bytes: Optional[int] = Field(default=None, sa_column=Column(BigInteger))
    storage_url: Optional[str] = Field(default=None, sa_column=Column(String))
    file_type: Optional[str] = Field(default=None, sa_column=Column(String))
    project_id: Optional[uuid.UUID] = Field(default=None, foreign_key="projects.id")
    meeting_id: Optional[uuid.UUID] = Field(default=None, foreign_key="meetings.id")
    owner_user_id: Optional[uuid.UUID] = Field(default=None, foreign_key="users.id")
    uploaded_by: Optional[uuid.UUID] = Field(default=None, foreign_key="users.id")
    extracted_text: Optional[str] = Field(default=None, sa_column=Column(Text))
    qdrant_vector_id: Optional[str] = Field(default=None, sa_column=Column(String))

    # Relationships
    project: Optional["Project"] = Relationship(back_populates="files")  # type: ignore
    meeting: Optional["Meeting"] = Relationship(back_populates="files")  # type: ignore
    owner_user: Optional["User"] = Relationship(back_populates="owned_files")  # type: ignore
    uploaded_by_user: "User" = Relationship(back_populates="uploaded_files")  # type: ignore
