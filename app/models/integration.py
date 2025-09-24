import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional

from sqlalchemy import JSON, Column, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from . import (
        User,
    )


class Integration(SQLModel, table=True):
    """Integration model"""

    __tablename__ = "integrations"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
    )
    updated_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True), onupdate=func.now()))

    user_id: uuid.UUID = Field(foreign_key="users.id", nullable=False)
    type: Optional[str] = Field(default=None, sa_column=Column(String))
    credentials_meta: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))

    # Relationships
    user: "User" = Relationship(
        back_populates="integrations",
        sa_relationship_kwargs={"foreign_keys": "Integration.user_id"},
    )  # type: ignore
