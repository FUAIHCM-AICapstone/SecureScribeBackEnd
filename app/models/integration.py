import uuid
from typing import Optional, Dict, Any

from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy import Column, String, JSON

from .base import BaseDatabaseModel


class Integration(BaseDatabaseModel, table=True):
    """Integration model"""

    __tablename__ = "integrations"

    project_id: uuid.UUID = Field(foreign_key="projects.id", nullable=False)
    type: Optional[str] = Field(default=None, sa_column=Column(String))
    credentials_meta: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))

    # Relationships
    project: "Project" = Relationship(back_populates="integrations")
