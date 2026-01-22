from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, String, Text
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

    id: int = Field(
        sa_column=Column(Integer, primary_key=True, autoincrement=True),
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True)))

    user_id: int = Field(foreign_key="users.id", nullable=False)
    agno_session_id: str = Field(sa_column=Column(String(255), nullable=False))
    title: Optional[str] = Field(default=None, sa_column=Column(String(255)))
    is_active: bool = Field(default=True, sa_column=Column(Boolean))

    # Relationships
    user: "User" = Relationship()
    messages: list["ChatMessage"] = Relationship(back_populates="conversation")


class ChatMessage(SQLModel, table=True):
    """Chat message model for storing conversation history"""

    __tablename__ = "chat_messages"

    id: int = Field(
        sa_column=Column(Integer, primary_key=True, autoincrement=True),
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    conversation_id: int = Field(foreign_key="conversations.id", nullable=False)
    message_type: str = Field(default=ChatMessageType.user, sa_column=Column(String(50)))
    content: str = Field(sa_column=Column(Text, nullable=False))
    mentions: Optional[list] = Field(default=None, sa_column=Column(JSON))
    message_metadata: Optional[dict] = Field(default=None, sa_column=Column(JSON))

    # Relationships
    conversation: Conversation = Relationship(back_populates="messages")
