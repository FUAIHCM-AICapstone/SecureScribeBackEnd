from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional

from sqlalchemy import JSON, Column, DateTime, Integer, String, func
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from . import (
        User,
    )


class AuditLog(SQLModel, table=True):
    """Audit log model"""

    __tablename__ = "audit_logs"

    id: int = Field(
        sa_column=Column(Integer, primary_key=True, autoincrement=True),
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
    )
    updated_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True), onupdate=func.now()))

    actor_user_id: int = Field(foreign_key="users.id", nullable=False)
    action: Optional[str] = Field(default=None, sa_column=Column(String(100)))
    target_type: Optional[str] = Field(default=None, sa_column=Column(String(100)))
    target_id: Optional[str] = Field(default=None, sa_column=Column(String(255)))
    audit_metadata: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))

    # Relationships
    actor_user: "User" = Relationship(
        back_populates="audit_logs",
        sa_relationship_kwargs={"foreign_keys": "AuditLog.actor_user_id"},
    )  # type: ignore
