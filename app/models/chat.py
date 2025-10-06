import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, Column, DateTime, String, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlmodel import Field, Relationship, SQLModel


class ChatMessageType(str, Enum):
    user = "user"
    agent = "agent"
    system = "system"


if TYPE_CHECKING:
    from . import User


class ChatSession(SQLModel, table=True):
    """Chat session model for user conversations"""

    __tablename__ = "chat_sessions"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True)))

    user_id: uuid.UUID = Field(foreign_key="users.id", nullable=False)
    agno_session_id: str = Field(sa_column=Column(String, nullable=False))
    title: Optional[str] = Field(default=None, sa_column=Column(String))
    is_active: bool = Field(default=True, sa_column=Column(Boolean))

    # Relationships
    user: "User" = Relationship()
    messages: list["ChatMessage"] = Relationship(back_populates="chat_session")


class ChatMessage(SQLModel, table=True):
    """Chat message model for storing conversation history"""

    __tablename__ = "chat_messages"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    chat_session_id: uuid.UUID = Field(foreign_key="chat_sessions.id", nullable=False)
    message_type: str = Field(default=ChatMessageType.user, sa_column=Column(String))
    content: str = Field(sa_column=Column(Text, nullable=False))
    mentions: list[dict] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False, default=list),
    )
    message_metadata: Optional[dict] = Field(default=None, sa_column=Column(JSON))

    # Relationships
    chat_session: ChatSession = Relationship(back_populates="messages")
