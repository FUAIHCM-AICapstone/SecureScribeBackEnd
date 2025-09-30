from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from .common import ApiResponse, PaginatedResponse


class ChatSessionCreate(BaseModel):
    title: Optional[str] = None


class ChatSessionUpdate(BaseModel):
    title: Optional[str] = None
    is_active: Optional[bool] = None


class ChatSessionResponse(BaseModel):
    id: UUID
    meeting_id: UUID
    user_id: UUID
    agno_session_id: str
    title: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ChatMessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)


class ChatMessageResponse(BaseModel):
    id: UUID
    chat_session_id: UUID
    message_type: str
    content: str
    message_metadata: Optional[dict] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ChatSessionWithMessages(ChatSessionResponse):
    messages: List[ChatMessageResponse] = Field(default_factory=list)
    message_count: int = 0


class ChatConversationResponse(BaseModel):
    session: ChatSessionResponse
    messages: List[ChatMessageResponse]
    total_messages: int
    meeting_title: Optional[str] = None


# API Response types
ChatSessionApiResponse = ApiResponse[ChatSessionResponse]
ChatSessionsPaginatedResponse = PaginatedResponse[ChatSessionResponse]
ChatMessageApiResponse = ApiResponse[ChatMessageResponse]
ChatMessagesPaginatedResponse = PaginatedResponse[ChatMessageResponse]
ChatConversationApiResponse = ApiResponse[ChatConversationResponse]
ChatSessionWithMessagesApiResponse = ApiResponse[ChatSessionWithMessages]


# WebSocket message types
class WSChatMessage(BaseModel):
    type: str = "chat_message"
    session_id: UUID
    message: ChatMessageResponse


class WSChatStatus(BaseModel):
    type: str = "chat_status"
    session_id: UUID
    status: str = "typing"  # Can be "typing", "processing", "ready"


class WSChatError(BaseModel):
    type: str = "chat_error"
    session_id: UUID
    error: str
    code: Optional[str] = None
