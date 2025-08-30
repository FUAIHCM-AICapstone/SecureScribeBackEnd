from datetime import datetime
from typing import Optional

from sqlalchemy import Column, DateTime, String, Text
from sqlmodel import Field

from .base import BaseDatabaseModel


class SearchDocument(BaseDatabaseModel, table=True):
    """Search document model"""

    __tablename__ = "search_documents"

    owner_type: Optional[str] = Field(default=None, sa_column=Column(String))
    owner_id: Optional[str] = Field(default=None, sa_column=Column(String))
    content_text: Optional[str] = Field(default=None, sa_column=Column(Text))
    qdrant_vector_id: Optional[str] = Field(default=None, sa_column=Column(String))
    indexed_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )
