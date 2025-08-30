import uuid
from typing import Optional, Dict, Any

from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy import Column, String, JSON

from .base import BaseDatabaseModel


class AuditLog(BaseDatabaseModel, table=True):
    """Audit log model"""

    __tablename__ = "audit_logs"

    actor_user_id: uuid.UUID = Field(foreign_key="users.id", nullable=False)
    action: Optional[str] = Field(default=None, sa_column=Column(String))
    target_type: Optional[str] = Field(default=None, sa_column=Column(String))
    target_id: Optional[str] = Field(default=None, sa_column=Column(String))
    metadata: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))

    # Relationships
    actor_user: "User" = Relationship(back_populates="audit_logs")
