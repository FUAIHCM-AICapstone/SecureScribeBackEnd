import uuid
from typing import Any, Dict, Optional

from sqlalchemy import JSON, Column, String
from sqlmodel import Field, Relationship

from .base import BaseDatabaseModel


class AuditLog(BaseDatabaseModel, table=True):
    """Audit log model"""

    __tablename__ = "audit_logs"

    actor_user_id: uuid.UUID = Field(foreign_key="users.id", nullable=False)
    action: Optional[str] = Field(default=None, sa_column=Column(String))
    target_type: Optional[str] = Field(default=None, sa_column=Column(String))
    target_id: Optional[str] = Field(default=None, sa_column=Column(String))
    audit_metadata: Optional[Dict[str, Any]] = Field(
        default=None, sa_column=Column(JSON)
    )

    # Relationships
    actor_user: "User" = Relationship(back_populates="audit_logs")  # type: ignore
