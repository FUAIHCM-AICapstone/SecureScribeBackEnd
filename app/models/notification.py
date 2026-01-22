from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional

from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, String, func
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from . import (
        User,
    )


class Notification(SQLModel, table=True):
    """Notification model"""

    __tablename__ = "notifications"

    id: int = Field(
        sa_column=Column(Integer, primary_key=True, autoincrement=True),
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
    )
    updated_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True), onupdate=func.now()))

    user_id: int = Field(foreign_key="users.id", nullable=False)
    type: Optional[str] = Field(default=None, sa_column=Column(String(50)))
    payload: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    is_read: bool = Field(default=False, sa_column=Column(Boolean))
    channel: Optional[str] = Field(default=None, sa_column=Column(String(100)))
    icon: Optional[str] = Field(default=None, sa_column=Column(String(255)))
    badge: Optional[str] = Field(default=None, sa_column=Column(String(100)))
    sound: Optional[str] = Field(default=None, sa_column=Column(String(255)))
    ttl: Optional[int] = Field(default=None, sa_column=Column(Integer))

    # Relationships
    user: "User" = Relationship(
        back_populates="notifications",
        sa_relationship_kwargs={"foreign_keys": "Notification.user_id"},
    )  # type: ignore
