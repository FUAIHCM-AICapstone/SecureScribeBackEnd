import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, DateTime, MetaData, func
from sqlalchemy.dialects.postgresql import UUID
from sqlmodel import Field, SQLModel

metadata = MetaData()


class BaseDatabaseModel(SQLModel):
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
    )
    updated_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True), onupdate=func.now()))


def get_uuid_column():
    try:
        from sqlalchemy.dialects.postgresql import UUID

        return UUID(as_uuid=True)
    except ImportError:
        from sqlalchemy import String

        return String


def get_json_column():
    try:
        from sqlalchemy.dialects.postgresql import JSON

        return JSON
    except ImportError:
        from sqlalchemy import JSON as SQLiteJSON

        return SQLiteJSON
