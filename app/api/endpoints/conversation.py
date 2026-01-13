import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.constants.messages import MessageConstants
from app.core.config import settings
from app.db import get_db
from app.models.user import User
from app.schemas.common import ApiResponse, create_pagination_meta
from app.schemas.conversation import (
    ConversationApiResponse,
    ConversationCreate,
    ConversationsPaginatedResponse,
    ConversationUpdate,
    ConversationWithMessagesApiResponse,
)
from app.services.conversation import (
    create_conversation,
    delete_conversation,
    get_conversation,
    get_conversation_with_messages,
    get_conversations_for_user,
    update_conversation,
)
from app.utils.auth import get_current_user

router = APIRouter(prefix=settings.API_V1_STR, tags=["Conversation"])


@router.post("/conversations", response_model=ConversationApiResponse)
def create_conversation_endpoint(
    conversation_data: ConversationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new conversation for the current user"""
    conversation = create_conversation(db, current_user.id, conversation_data)

    return ApiResponse(success=True, message=MessageConstants.CONVERSATION_CREATED_SUCCESS, data=conversation)


@router.get("/conversations", response_model=ConversationsPaginatedResponse)
def get_user_conversations_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    """Get conversations for the current user"""
    conversations, total = get_conversations_for_user(db, current_user.id, page, limit)

    pagination_meta = create_pagination_meta(page, limit, total)

    return ConversationsPaginatedResponse(
        success=True,
        message=MessageConstants.CONVERSATION_RETRIEVED_SUCCESS,
        data=conversations,
        pagination=pagination_meta,
    )


@router.get("/conversations/{conversation_id}", response_model=ConversationApiResponse)
def get_conversation_endpoint(
    conversation_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific conversation"""
    conversation = get_conversation(db, conversation_id, current_user.id)
    if not conversation:
        raise HTTPException(status_code=404, detail=MessageConstants.CONVERSATION_NOT_FOUND)

    return ApiResponse(success=True, message=MessageConstants.CONVERSATION_RETRIEVED_SUCCESS, data=conversation)


@router.put("/conversations/{conversation_id}", response_model=ConversationApiResponse)
def update_conversation_endpoint(
    conversation_id: uuid.UUID,
    update_data: ConversationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a conversation"""
    conversation = update_conversation(db, conversation_id, current_user.id, update_data)
    if not conversation:
        raise HTTPException(status_code=404, detail=MessageConstants.CONVERSATION_NOT_FOUND)

    return ApiResponse(success=True, message=MessageConstants.CONVERSATION_UPDATED_SUCCESS, data=conversation)


@router.delete("/conversations/{conversation_id}", response_model=ApiResponse[None])
def delete_conversation_endpoint(
    conversation_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a conversation"""
    success = delete_conversation(db, conversation_id, current_user.id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=MessageConstants.CONVERSATION_NOT_FOUND)

    return ApiResponse(success=True, message=MessageConstants.CONVERSATION_DELETED_SUCCESS, data=None)


@router.get("/conversations/{conversation_id}/messages", response_model=ConversationWithMessagesApiResponse)
def get_conversation_with_messages_endpoint(
    conversation_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = Query(50, ge=1, le=200),
):
    """Get a conversation with its messages"""
    conversation = get_conversation_with_messages(db, conversation_id, current_user.id, limit)
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=MessageConstants.CONVERSATION_NOT_FOUND)

    return ApiResponse(success=True, message=MessageConstants.CONVERSATION_RETRIEVED_SUCCESS, data=conversation)
