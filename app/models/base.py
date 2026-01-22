from datetime import datetime
from typing import Optional

from sqlalchemy import Column, DateTime, Integer, MetaData, String, func
from sqlmodel import Field, SQLModel

metadata = MetaData()


class BaseDatabaseModel(SQLModel):
    id: int = Field(
        sa_column=Column(Integer, primary_key=True, autoincrement=True),
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
    )
    updated_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True), onupdate=func.now()))


def get_id_column():
    """Get integer column type for current database dialect"""
    return Integer


def get_json_column():
    """Get JSON column type for current database dialect"""
    from sqlalchemy import JSON

    return JSON
