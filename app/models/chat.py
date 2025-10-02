import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import JSON, Boolean, Column, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlmodel import Field, Relationship, SQLModel


class ChatMessageType(str, Enum):
    user = "user"
    agent = "agent"
    system = "system"


if TYPE_CHECKING:
    from . import User


class Conversation(SQLModel, table=True):
    """Chat session model for user conversations"""

    __tablename__ = "conversations"

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
    messages: list["ChatMessage"] = Relationship(back_populates="conversation")


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

    conversation_id: uuid.UUID = Field(foreign_key="conversations.id", nullable=False)
    message_type: str = Field(default=ChatMessageType.user, sa_column=Column(String))
    content: str = Field(sa_column=Column(Text, nullable=False))
    mentions: Optional[list] = Field(default=None, sa_column=Column(JSON))
    message_metadata: Optional[dict] = Field(default=None, sa_column=Column(JSON))

    # Relationships
    conversation: Conversation = Relationship(back_populates="messages")
