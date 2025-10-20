import asyncio
import json
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import SessionLocal, get_db
from app.jobs.tasks import process_chat_message
from app.models.chat import ChatMessageType, Conversation
from app.models.user import User
from app.schemas.chat import (
    ChatMessageApiResponse,
    ChatMessageCreate,
)
from app.schemas.common import ApiResponse
from app.services.chat import (
    create_chat_message,
    query_documents_for_mentions,
)
from app.services.conversation import get_conversation
from app.utils.auth import get_current_user
from app.utils.redis import get_async_redis_client

router = APIRouter(prefix=settings.API_V1_STR, tags=["Chat"])


@router.post("/conversations/{conversation_id}/messages", response_model=ChatMessageApiResponse)
async def send_chat_message_endpoint(
    conversation_id: uuid.UUID,
    message_data: ChatMessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),  # Adapted to use get_current_user
):
    """Send a message to a conversation and trigger background AI processing"""
    # Create user message with mentions (existing logic)
    user_message = create_chat_message(db=db, conversation_id=conversation_id, user_id=current_user.id, content=message_data.content, message_type=ChatMessageType.user, mentions=message_data.mentions)
    if not user_message:
        raise HTTPException(status_code=404, detail="Conversation not found or inactive")

    # Get conversation for context (existing logic)
    conversation = get_conversation(db, conversation_id, current_user.id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Handle mention-based querying (adapted from Agno_chat)
    query_results = []
    if message_data.mentions:
        query_results = await query_documents_for_mentions(message_data.mentions)

    # Trigger background AI processing task (core Agno_chat logic)
    task = process_chat_message.delay(conversation_id=str(conversation_id), user_message_id=str(user_message.id), content=message_data.content, user_id=current_user.id, query_results=query_results)

    print(f"Triggered background task {task.id} for conversation_id={conversation_id}")

    # Return user message + task_id immediately (Agno_chat logic)
    return ApiResponse(  # Standardized to SecureScribeBackEnd's ApiResponse
        success=True,
        message="Message sent and background AI processing started",
        data={
            "user_message": {"id": str(user_message.id), "conversation_id": str(user_message.conversation_id), "role": "user", "content": user_message.content, "timestamp": user_message.created_at.isoformat(), "mentions": user_message.mentions if isinstance(user_message.mentions, list) else []},
            "task_id": task.id,
            "ai_message": None,  # AI response will come via SSE
        },
    )


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
            conversation = db.query(Conversation).filter(Conversation.id == conversation_id, Conversation.is_active == True).first()
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

                    if message and message["type"] == "message":
                        # Parse and forward the message
                        data = json.loads(message["data"])
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
        },
    )
