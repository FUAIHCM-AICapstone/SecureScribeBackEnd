import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from sqlmodel import Field, SQLModel
from sqlalchemy import Column, DateTime, func, MetaData
from sqlalchemy.dialects.postgresql import UUID


# Create metadata for SQLModel
metadata = MetaData()


class BaseDatabaseModel(SQLModel):
    """Base model with common database fields and methods"""

    metadata = metadata

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    )

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), default=func.now(), nullable=False)
    )

    updated_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), default=None, onupdate=func.now())
    )

    class Config:
        arbitrary_types_allowed = True
        from_attributes = True

    def update_timestamp(self) -> None:
        """Update the updated_at timestamp"""
        self.updated_at = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary"""
        return self.model_dump()

    def to_dict_exclude_none(self) -> Dict[str, Any]:
        """Convert model to dictionary excluding None values"""
        return self.model_dump(exclude_none=True)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BaseDatabaseModel":
        """Create model instance from dictionary"""
        return cls(**data)
