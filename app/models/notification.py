import uuid
from typing import Any, Dict, Optional

from sqlalchemy import JSON, Boolean, Column, String
from sqlmodel import Field, Relationship

from .base import BaseDatabaseModel


class Notification(BaseDatabaseModel, table=True):
    """Notification model"""

    __tablename__ = "notifications"

    user_id: uuid.UUID = Field(foreign_key="users.id", nullable=False)
    type: Optional[str] = Field(default=None, sa_column=Column(String))
    payload: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    is_read: bool = Field(default=False, sa_column=Column(Boolean))
    channel: Optional[str] = Field(default=None, sa_column=Column(String))

    # Relationships
    user: "User" = Relationship(back_populates="notifications")  # type: ignore
