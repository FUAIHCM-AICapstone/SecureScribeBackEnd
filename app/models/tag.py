import uuid
from typing import Optional

from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy import Column, String

from .base import BaseDatabaseModel


class Tag(BaseDatabaseModel, table=True):
    """Tag model"""

    __tablename__ = "tags"

    name: str = Field(sa_column=Column(String, nullable=False))
    created_by: uuid.UUID = Field(foreign_key="users.id", nullable=False)
    scope: str = Field(default="global", sa_column=Column(String))

    # Relationships
    created_by_user: "User" = Relationship(back_populates="created_tags")
    meetings: list["MeetingTag"] = Relationship(back_populates="tag")


class MeetingTag(SQLModel, table=True):
    """Junction table for meetings and tags (many-to-many relationship)"""

    __tablename__ = "meeting_tags"

    meeting_id: uuid.UUID = Field(foreign_key="meetings.id", primary_key=True)
    tag_id: uuid.UUID = Field(foreign_key="tags.id", primary_key=True)

    # Relationships
    meeting: "Meeting" = Relationship(back_populates="tags")
    tag: Tag = Relationship(back_populates="meetings")
