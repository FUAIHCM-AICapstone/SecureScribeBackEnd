import uuid
from typing import Any, Dict, Optional

from sqlalchemy import JSON, Column, String
from sqlmodel import Field, Relationship

from .base import BaseDatabaseModel


class Integration(BaseDatabaseModel, table=True):
    """Integration model"""

    __tablename__ = "integrations"

    project_id: uuid.UUID = Field(foreign_key="projects.id", nullable=False)
    type: Optional[str] = Field(default=None, sa_column=Column(String))
    credentials_meta: Optional[Dict[str, Any]] = Field(
        default=None, sa_column=Column(JSON)
    )

    # Relationships
    project: "Project" = Relationship(back_populates="integrations")  # type: ignore
