import asyncio
import json
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import SessionLocal, get_db
from app.models.chat import ChatMessageType, Conversation
from app.models.user import User
from app.schemas.chat import (
    ChatMessageApiResponse,
    ChatMessageCreate,
    ConversationApiResponse,
    ConversationCreate,
    ConversationsPaginatedResponse,
    ConversationUpdate,
)
from app.schemas.common import ApiResponse, create_pagination_meta
from app.services.chat import (
    create_chat_message,
    delete_conversation,
    get_conversation,
    query_documents_for_mentions,
    update_conversation,
)
from app.services.conversation import (
    create_conversation,
    get_conversations_for_user,
)
from app.utils.auth import get_current_user
from app.utils.redis import get_async_redis_client

router = APIRouter(prefix=settings.API_V1_STR, tags=["Chat"])


# ===== CHAT SESSION ENDPOINTS =====


@router.post("/conversations", response_model=ConversationApiResponse)
def create_conversation_endpoint(
    session_data: ConversationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new conversation for the current user"""
    conversation = create_conversation(db, current_user.id, session_data)

    return ApiResponse(success=True, message="Conversation created successfully", data=conversation)


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
        message="Conversations retrieved successfully",
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
        raise HTTPException(status_code=404, detail="Conversation not found")

    return ApiResponse(success=True, message="Conversation retrieved successfully", data=conversation)


@router.put("/conversations/{conversation_id}", response_model=ConversationApiResponse)
def update_conversation_endpoint(
    conversation_id: uuid.UUID,
    update_data: ConversationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a conversation"""
    conversation = update_conversation(db, conversation_id, current_user.id, update_data.dict())
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return ApiResponse(success=True, message="Conversation updated successfully", data=conversation)


@router.delete("/conversations/{conversation_id}", response_model=ApiResponse[None])
def delete_conversation_endpoint(
    conversation_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a conversation"""
    success = delete_conversation(db, conversation_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return ApiResponse(success=True, message="Conversation deleted successfully", data=None)


# ===== CHAT MESSAGE ENDPOINTS =====


@router.post("/conversations/{conversation_id}/messages", response_model=ChatMessageApiResponse)
async def send_chat_message_endpoint(
    conversation_id: uuid.UUID,
    message_data: ChatMessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Send a message to a conversation and get AI response"""
    # Create user message with mentions
    user_message = create_chat_message(
        db=db,
        conversation_id=conversation_id,
        user_id=current_user.id,
        content=message_data.content,
        message_type=ChatMessageType.user,
        mentions=message_data.mentions
    )
    if not user_message:
        raise HTTPException(status_code=404, detail="Conversation not found or inactive")

    # Get conversation for context
    conversation = get_conversation(db, conversation_id, current_user.id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Handle mention-based querying (for now just prints as requested)
    if message_data.mentions:
        query_documents_for_mentions(message_data.mentions, str(current_user.id))

    try:
        # For now, create a simple AI response
        # TODO: Integrate with proper LLM when ready
        ai_response_content = f"I received your message: '{message_data.content}'. This is a placeholder response."

        # Create AI message
        ai_message = create_chat_message(
            db=db,
            conversation_id=conversation_id,
            user_id=current_user.id,
            content=ai_response_content,
            message_type=ChatMessageType.agent
        )

        # Broadcast message via Redis to SSE channel
        redis_client = await get_async_redis_client()
        channel = f"conversation:{conversation_id}:messages"
        message_data = {
            "type": "chat_message",
            "conversation_id": str(conversation_id),
            "message": {
                "id": str(ai_message.id),
                "content": ai_response_content,
                "message_type": "agent",
                "created_at": ai_message.created_at.isoformat()
            }
        }
        await redis_client.publish(channel, json.dumps(message_data))

        # Return both user and AI messages as per API spec
        return ApiResponse(success=True, message="Message sent and response received", data={
            "user_message": {
                "id": str(user_message.id),
                "conversation_id": str(user_message.conversation_id),
                "role": "user",
                "content": user_message.content,
                "timestamp": user_message.created_at.isoformat(),
                "mentions": user_message.mentions
            },
            "ai_message": {
                "id": str(ai_message.id),
                "conversation_id": str(ai_message.conversation_id),
                "role": "assistant",
                "content": ai_message.content,
                "timestamp": ai_message.created_at.isoformat(),
                "mentions": ai_message.mentions or []
            }
        })

    except Exception:
        # Return user message only if AI generation failed
        return ApiResponse(success=True, message="Message sent but AI response failed", data={
            "user_message": {
                "id": str(user_message.id),
                "conversation_id": str(user_message.conversation_id),
                "role": "user",
                "content": user_message.content,
                "timestamp": user_message.created_at.isoformat(),
                "mentions": user_message.mentions
            },
            "ai_message": None
        })

# ===== SSE CHAT ENDPOINT =====


@router.get("/conversations/{conversation_id}/events")
async def chat_sse_endpoint(
    conversation_id: uuid.UUID,
):
    """
    SSE endpoint for real-time chat messages.
    Establishes a server-sent events connection for chat updates.
    """

    async def event_generator() -> AsyncGenerator[str, None]:
        """Generate SSE events for chat messages"""
        # Verify conversation access
        db = SessionLocal()
        try:
            # For SSE, we'll use a simpler approach - just verify the conversation exists
            # In a real app, you'd want to authenticate the SSE connection properly
            conversation = db.query(Conversation).filter(
                Conversation.id == conversation_id,
                Conversation.is_active == True
            ).first()
            if not conversation:
                yield f"data: {json.dumps({'error': 'Conversation not found'})}\n\n"
                return
        finally:
            db.close()

        # Send initial connection event
        yield f"data: {json.dumps({'type': 'connected', 'conversation_id': str(conversation_id)})}\n\n"

        # Subscribe to Redis channel for this conversation
        redis_client = await get_async_redis_client()
        # For now, we'll use a general channel - in production you'd want user-specific channels
        channel = f"conversation:{conversation_id}:messages"

        try:
            # Subscribe to Redis channel
            pubsub = redis_client.pubsub()
            await pubsub.subscribe(channel)

            # Keep connection alive and listen for messages
            while True:
                try:
                    # Wait for message from Redis
                    message = await pubsub.get_message(timeout=30.0)

                    if message and message['type'] == 'message':
                        # Parse and forward the message
                        data = json.loads(message['data'])
                        yield f"data: {json.dumps(data)}\n\n"
                    else:
                        # Send heartbeat if no message received
                        yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"

                except asyncio.TimeoutError:
                    # Send heartbeat on timeout
                    yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
                except Exception as e:
                    print(f"SSE error: {e}")
                    break

        except asyncio.CancelledError:
            # Client disconnected
            pass
        finally:
            # Cleanup Redis subscription
            try:
                await pubsub.unsubscribe(channel)
                await pubsub.close()
            except Exception:
                pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control",
        }
    )
