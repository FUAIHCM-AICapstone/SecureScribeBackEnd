import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional

from sqlalchemy import JSON, Column, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from . import (
        Project,
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
        sa_column=Column(
            DateTime(timezone=True), server_default=func.now(), nullable=False
        ),
    )
    updated_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True), onupdate=func.now())
    )

    project_id: uuid.UUID = Field(foreign_key="projects.id", nullable=False)
    type: Optional[str] = Field(default=None, sa_column=Column(String))
    credentials_meta: Optional[Dict[str, Any]] = Field(
        default=None, sa_column=Column(JSON)
    )

    # Relationships
    project: "Project" = Relationship(
        back_populates="integrations",
        sa_relationship_kwargs={"foreign_keys": "Integration.project_id"},
    )  # type: ignore
