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
)
from app.schemas.common import ApiResponse
from app.services.chat import (
    create_chat_message,
    get_conversation,
    get_recent_messages,
    query_documents_for_mentions,
)
from app.utils.auth import get_current_user
from app.utils.redis import get_async_redis_client
from app.utils.llm import chat_complete

router = APIRouter(prefix=settings.API_V1_STR, tags=["Chat"])


@router.post("/conversations/{conversation_id}/messages", response_model=ChatMessageApiResponse)
async def send_chat_message_endpoint(
    conversation_id: uuid.UUID,
    message_data: ChatMessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Send a message to a conversation and get AI response"""
    # Create user message with mentions
    user_message = create_chat_message(db=db, conversation_id=conversation_id, user_id=current_user.id, content=message_data.content, message_type=ChatMessageType.user, mentions=message_data.mentions)
    if not user_message:
        raise HTTPException(status_code=404, detail="Conversation not found or inactive")

    # Get conversation for context
    conversation = get_conversation(db, conversation_id, current_user.id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Handle mention-based querying (for now just prints as requested)
    if message_data.mentions:
        query_documents_for_mentions(message_data.mentions, str(current_user.id))

    def _serialize_message(db_message):
        return {
            "id": str(db_message.id),
            "conversation_id": str(db_message.conversation_id),
            "role": (
                "assistant"
                if db_message.message_type == ChatMessageType.agent
                else "user"
                if db_message.message_type == ChatMessageType.user
                else "system"
            ),
            "content": db_message.content,
            "timestamp": db_message.created_at.isoformat(),
            "mentions": db_message.mentions if isinstance(db_message.mentions, list) else [],
        }

    try:
        recent_messages = get_recent_messages(db, conversation_id, limit=5)
        if not any(msg.id == user_message.id for msg in recent_messages):
            recent_messages.append(user_message)
        recent_messages.sort(key=lambda msg: msg.created_at)

        transcript_lines = []
        for msg in recent_messages:
            role_label = "User"
            if msg.message_type == ChatMessageType.agent:
                role_label = "Assistant"
            elif msg.message_type != ChatMessageType.user:
                role_label = "System"
            transcript_lines.append(f"{role_label}: {msg.content}")
        transcript_text = "\n".join(transcript_lines)

        system_prompt = "You are SecureScribe's AI assistant. Use the conversation transcript to provide a concise, helpful reply."
        user_prompt = f"Conversation transcript:\n{transcript_text}\n\nCurrent user message: {message_data.content}"

        ai_response_content = await chat_complete(system_prompt, user_prompt)

        # Create AI message
        ai_message = create_chat_message(db=db, conversation_id=conversation_id, user_id=current_user.id, content=ai_response_content, message_type=ChatMessageType.agent)

        # Broadcast message via Redis to SSE channel
        redis_client = await get_async_redis_client()
        channel = f"conversation:{conversation_id}:messages"
        message_data = {
            "type": "chat_message",
            "conversation_id": str(conversation_id),
            "message": _serialize_message(ai_message),
        }
        await redis_client.publish(channel, json.dumps(message_data))

        # Return both user and AI messages as per API spec
        return ApiResponse(success=True, message="Message sent and response received", data={"user_message": _serialize_message(user_message), "ai_message": _serialize_message(ai_message)})

    except Exception:
        # Return user message only if AI generation failed
        return ApiResponse(success=True, message="Message sent but AI response failed", data={"user_message": _serialize_message(user_message), "ai_message": None})


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
