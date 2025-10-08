from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from .common import PaginationMeta


class Mention(BaseModel):
    """Schema for message mentions"""

    entity_type: str  # "project", "meeting", "file"
    entity_id: str  # UUID string
    offset_start: int
    offset_end: int


class ChatMessageCreate(BaseModel):
    """Schema for creating chat messages"""

    content: str
    mentions: Optional[List[Mention]] = None


class ChatMessageResponse(BaseModel):
    """Schema for chat message in API responses"""

    id: UUID
    conversation_id: UUID
    role: str = Field(alias="message_type")  # "user", "assistant", "system"
    content: str
    timestamp: datetime = Field(alias="created_at")
    mentions: Optional[List[Mention]] = None

    class Config:
        from_attributes = True


class ChatConversationResponse(BaseModel):
    """Schema for conversation with messages"""

    id: UUID
    title: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    is_active: bool
    messages: List[ChatMessageResponse]

    class Config:
        from_attributes = True


class ConversationCreate(BaseModel):
    """Schema for creating conversations"""

    title: Optional[str] = None


class ConversationUpdate(BaseModel):
    """Schema for updating conversations"""

    title: Optional[str] = None
    is_active: Optional[bool] = None


class ConversationResponse(BaseModel):
    """Schema for conversation in API responses"""

    id: UUID
    user_id: UUID
    agno_session_id: str
    title: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    is_active: bool

    class Config:
        from_attributes = True


class ConversationsPaginatedResponse(BaseModel):
    """Schema for paginated conversations response"""

    success: bool
    message: str
    data: List[ConversationResponse]
    pagination: Optional[PaginationMeta] = None


class ChatMessageApiResponse(BaseModel):
    """Schema for chat message API response"""

    success: bool
    message: str
    data: dict  # Can contain user_message and ai_message


class ChatConversationApiResponse(BaseModel):
    """Schema for chat conversation API response"""

    success: bool
    message: str
    data: ChatConversationResponse


class ConversationApiResponse(BaseModel):
    """Schema for conversation API response"""

    success: bool
    message: str
    data: ConversationResponse
