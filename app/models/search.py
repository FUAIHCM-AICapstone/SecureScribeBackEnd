import uuid
from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy import Column, String, Text, DateTime

from .base import BaseDatabaseModel


class SearchDocument(BaseDatabaseModel, table=True):
    """Search document model"""

    __tablename__ = "search_documents"

    owner_type: Optional[str] = Field(default=None, sa_column=Column(String))
    owner_id: Optional[uuid.UUID] = Field(default=None, sa_column=Column(String))
    content_text: Optional[str] = Field(default=None, sa_column=Column(Text))
    qdrant_vector_id: Optional[str] = Field(default=None, sa_column=Column(String))
    indexed_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True)))
