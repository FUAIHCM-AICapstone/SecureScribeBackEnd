from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel

from .chat import ChatMessageResponse
from .common import PaginationMeta


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
    title: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    is_active: bool
    message_count: int = 0

    class Config:
        from_attributes = True


class ConversationWithMessagesResponse(BaseModel):
    """Schema for conversation with messages"""

    id: UUID
    user_id: UUID
    title: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    is_active: bool
    messages: List[ChatMessageResponse]

    class Config:
        from_attributes = True


class ConversationsPaginatedResponse(BaseModel):
    """Schema for paginated conversations response"""

    success: bool
    message: str
    data: List[ConversationResponse]
    pagination: Optional[PaginationMeta] = None


class ConversationApiResponse(BaseModel):
    """Schema for conversation API response"""

    success: bool
    message: str
    data: ConversationResponse


class ConversationWithMessagesApiResponse(BaseModel):
    """Schema for conversation with messages API response"""

    success: bool
    message: str
    data: ConversationWithMessagesResponse
