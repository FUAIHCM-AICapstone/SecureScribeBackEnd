import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Column, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlmodel import Field, SQLModel

if TYPE_CHECKING:
    pass


class SearchDocument(SQLModel, table=True):
    """Search document model"""

    __tablename__ = "search_documents"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
    )
    updated_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True), onupdate=func.now()))

    owner_type: Optional[str] = Field(default=None, sa_column=Column(String))
    owner_id: Optional[str] = Field(default=None, sa_column=Column(String))
    content_text: Optional[str] = Field(default=None, sa_column=Column(Text))
    qdrant_vector_id: Optional[str] = Field(default=None, sa_column=Column(String))
    indexed_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True)))
