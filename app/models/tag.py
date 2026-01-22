from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Column, DateTime, Integer, String, func
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from . import Meeting, MeetingTag, Tag, User


class Tag(SQLModel, table=True):
    """Tag model"""

    __tablename__ = "tags"

    id: int = Field(
        sa_column=Column(Integer, primary_key=True, autoincrement=True),
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
    )
    updated_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True), onupdate=func.now()))

    name: str = Field(sa_column=Column(String(255), nullable=False))
    created_by: int = Field(foreign_key="users.id", nullable=False)
    scope: str = Field(default="global", sa_column=Column(String(50)))

    # Relationships
    created_by_user: "User" = Relationship(
        back_populates="created_tags",
        sa_relationship_kwargs={"foreign_keys": "Tag.created_by"},
    )  # type: ignore
    meetings: list["MeetingTag"] = Relationship(back_populates="tag")


class MeetingTag(SQLModel, table=True):
    """Junction table for meetings and tags (many-to-many relationship)"""

    __tablename__ = "meeting_tags"

    meeting_id: int = Field(foreign_key="meetings.id", primary_key=True)
    tag_id: int = Field(foreign_key="tags.id", primary_key=True)

    # Relationships
    meeting: "Meeting" = Relationship(
        back_populates="tags",
        sa_relationship_kwargs={"foreign_keys": "MeetingTag.meeting_id"},
    )  # type: ignore
    tag: Tag = Relationship(
        back_populates="meetings",
        sa_relationship_kwargs={"foreign_keys": "MeetingTag.tag_id"},
    )
