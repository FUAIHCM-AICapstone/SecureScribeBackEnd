import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import SessionLocal, get_db
from app.models.chat import ChatMessageType
from app.models.user import User
from app.schemas.chat import (
    ChatConversationApiResponse,
    ChatMessageApiResponse,
    ChatMessageCreate,
    ChatSessionApiResponse,
    ChatSessionCreate,
    ChatSessionsPaginatedResponse,
    ChatSessionUpdate,
)
from app.schemas.common import ApiResponse, create_pagination_meta
from app.services.chat import (
    create_chat_message,
    create_chat_session,
    delete_chat_session,
    get_chat_history,
    get_chat_session,
    get_chat_session_with_messages,
    get_chat_sessions_for_meeting,
    update_chat_session,
)
from app.services.chat_agent import get_meeting_chat_agent, prime_agent_with_history
from app.services.user import get_user_by_id
from app.services.websocket_manager import websocket_manager
from app.utils.auth import get_current_user, get_current_user_from_token

router = APIRouter(prefix=settings.API_V1_STR, tags=["Chat"])


# ===== CHAT SESSION ENDPOINTS =====


@router.post("/meetings/{meeting_id}/chat/sessions", response_model=ChatSessionApiResponse)
def create_chat_session_endpoint(
    meeting_id: uuid.UUID,
    session_data: ChatSessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new chat session for a meeting"""
    session = create_chat_session(db, meeting_id, current_user.id, session_data)
    if not session:
        raise HTTPException(status_code=404, detail="Meeting not found or access denied")

    return ApiResponse(success=True, message="Chat session created successfully", data=session)


@router.get("/meetings/{meeting_id}/chat/sessions", response_model=ChatSessionsPaginatedResponse)
def get_meeting_chat_sessions_endpoint(
    meeting_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    """Get chat sessions for a meeting"""
    sessions, total = get_chat_sessions_for_meeting(db, meeting_id, current_user.id, page, limit)

    pagination_meta = create_pagination_meta(page, limit, total)

    return ChatSessionsPaginatedResponse(
        success=True,
        message="Chat sessions retrieved successfully",
        data=sessions,
        pagination=pagination_meta,
    )


@router.get("/chat/sessions/{session_id}", response_model=ChatSessionApiResponse)
def get_chat_session_endpoint(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific chat session"""
    session = get_chat_session(db, session_id, current_user.id)
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    return ApiResponse(success=True, message="Chat session retrieved successfully", data=session)


@router.put("/chat/sessions/{session_id}", response_model=ChatSessionApiResponse)
def update_chat_session_endpoint(
    session_id: uuid.UUID,
    update_data: ChatSessionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a chat session"""
    session = update_chat_session(db, session_id, current_user.id, update_data)
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    return ApiResponse(success=True, message="Chat session updated successfully", data=session)


@router.delete("/chat/sessions/{session_id}", response_model=ApiResponse[None])
def delete_chat_session_endpoint(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a chat session"""
    success = delete_chat_session(db, session_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Chat session not found")

    return ApiResponse(success=True, message="Chat session deleted successfully", data=None)


@router.get("/meetings/{meeting_id}/chat/{session_id}/history")
def get_chat_history_endpoint(
    meeting_id: uuid.UUID,
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get full chat history for a session"""
    session = get_chat_session(db, session_id, current_user.id)
    if not session or session.meeting_id != meeting_id:
        raise HTTPException(status_code=404, detail="Chat session not found")

    messages = get_chat_history(db, session_id, current_user.id, limit=1000)

    history = []
    for message in messages:
        sender = "user"
        if message.message_type == ChatMessageType.agent:
            sender = "agent"
        elif message.message_type == ChatMessageType.system:
            sender = "system"

        history.append(
            {
                "sender": sender,
                "message": message.content,
                "timestamp": message.created_at.isoformat(),
            }
        )

    return ApiResponse(
        success=True,
        message="Chat history retrieved successfully",
        data=history,
    )



# ===== CHAT MESSAGE ENDPOINTS =====

@router.post("/chat/sessions/{session_id}/messages", response_model=ChatMessageApiResponse)
async def send_chat_message_endpoint(
    session_id: uuid.UUID,
    message_data: ChatMessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Send a message to a chat session and get agent response"""
    # Create user message
    user_message = create_chat_message(
        db, session_id, current_user.id, message_data.content, ChatMessageType.user
    )
    if not user_message:
        raise HTTPException(
            status_code=404, detail="Chat session not found or inactive"
        )

    # Get session to determine meeting
    session = get_chat_session(db, session_id, current_user.id)
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    # Create agent
    agent = get_meeting_chat_agent(
        db, current_user.id, session.meeting_id, session.agno_session_id
    )
    if not agent:
        raise HTTPException(status_code=500, detail="Failed to create chat agent")

    history_messages = get_chat_history(
        db,
        session_id,
        current_user.id,
        exclude_message_ids={user_message.id},
    )
    prime_agent_with_history(agent, history_messages)

    try:
        # Get agent response (arun is async version)
        agent_response_obj = await agent.arun(message_data.content)
        agent_response = (
            agent_response_obj.content
            if hasattr(agent_response_obj, "content")
            else str(agent_response_obj)
        )

        # Create agent message
        agent_message = create_chat_message(
            db, session_id, current_user.id, agent_response, ChatMessageType.agent
        )

        # Broadcast to WebSocket if connected
        await websocket_manager.publish_user_message(
            str(current_user.id),
            {
                "type": "chat_message",
                "session_id": str(session_id),
                "message": {
                    "id": str(agent_message.id),
                    "content": agent_response,
                    "message_type": "agent",
                    "created_at": agent_message.created_at.isoformat(),
                },
            },
        )

        return ApiResponse(
            success=True,
            message="Message sent and response received",
            data=agent_message,
        )

    except Exception as e:
        # Create error response
        error_message = f"I apologize, but I encountered an error: {str(e)}"
        agent_message = create_chat_message(
            db, session_id, current_user.id, error_message, ChatMessageType.agent
        )

        return ApiResponse(
            success=True, message="Message sent with error response", data=agent_message
        )


# ===== WEBSOCKET CHAT ENDPOINT =====

@router.websocket("/chat/sessions/{session_id}/ws")
async def chat_websocket_endpoint(
    websocket: WebSocket,
    session_id: uuid.UUID,
    authorization: str = Query(None, description="Bearer token in format: Bearer <token>"),
    token: str = Query(None, description="JWT token (legacy support)"),
):
    """WebSocket endpoint for real-time chat"""

    user_id = None
    user_uuid: Optional[uuid.UUID] = None
    db = None

    try:
        # Get token
        auth_token = None
        if authorization and authorization.lower().startswith("bearer "):
            auth_token = authorization[len("bearer ") :].strip()
        elif authorization:
            auth_token = authorization.strip()
        elif token:
            auth_token = token.strip()

        if not auth_token:
            await websocket.close(code=4001, reason="Missing token")
            return

        # Authenticate user
        user_id = get_current_user_from_token(auth_token)
        if not user_id:
            await websocket.close(code=4001, reason="Invalid token")
            return

        try:
            user_uuid = uuid.UUID(user_id)
        except ValueError:
            await websocket.close(code=4001, reason="Invalid token")
            return

        # Validate user exists
        db = SessionLocal()
        try:
            user = get_user_by_id(db, user_uuid)
            if not user:
                await websocket.close(code=4002, reason="User not found")
                return
        finally:
            db.close()

        print(f"WebSocket connected for user: {user.id}")

        # Get db session for chat
        db = SessionLocal()

        # Verify session access
        session = get_chat_session(db, session_id, user_uuid)
        if not session:
            await websocket.close(code=4002, reason="Chat session not found")
            return

        # Accept connection
        await websocket.accept()

        # Add to connection manager
        connection_key = f"chat_{session_id}_{user_id}"
        websocket_manager.add_connection(connection_key, websocket)

        # Create agent
        agent = get_meeting_chat_agent(
            db, user_uuid, session.meeting_id, session.agno_session_id
        )

        if agent:
            history_messages = get_chat_history(db, session_id, user_uuid)
            prime_agent_with_history(agent, history_messages)

        # Main message loop
        while True:
            try:
                # Receive message
                data = await websocket.receive_json()
                message_content = data.get("content", "")

                if not message_content:
                    continue

                # Create user message
                user_message = create_chat_message(
                    db,
                    session_id,
                    user_uuid,
                    message_content,
                    ChatMessageType.user,
                )

                if not user_message:
                    await websocket.send_json({"type": "chat_error", "error": "Chat session unavailable"})
                    continue

                # Send typing indicator
                await websocket.send_json({"type": "chat_status", "status": "processing"})

                # Get agent response
                if agent:
                    history_messages = get_chat_history(
                        db,
                        session_id,
                        user_uuid,
                        exclude_message_ids={user_message.id},
                    )
                    prime_agent_with_history(agent, history_messages)

                    agent_response_obj = await agent.arun(message_content)
                    agent_response = (
                        agent_response_obj.content
                        if hasattr(agent_response_obj, "content")
                        else str(agent_response_obj)
                    )

                    # Create agent message
                    agent_message = create_chat_message(
                        db,
                        session_id,
                        user_uuid,
                        agent_response,
                        ChatMessageType.agent,
                    )

                    # Send response
                    await websocket.send_json(
                        {
                            "type": "chat_message",
                            "message": {
                                "id": str(agent_message.id),
                                "content": agent_response,
                                "message_type": "agent",
                                "created_at": agent_message.created_at.isoformat(),
                            },
                        }
                    )
                else:
                    await websocket.send_json({"type": "chat_error", "error": "Agent unavailable"})

            except WebSocketDisconnect:
                break
            except Exception as e:
                await websocket.send_json({"type": "chat_error", "error": str(e)})

    except Exception:
        try:
            await websocket.close(code=4000, reason="Connection error")
        except:
            pass

    finally:
        if user_id:
            connection_key = f"chat_{session_id}_{user_id}"
            try:
                websocket_manager.remove_connection(connection_key, websocket)
            except:
                pass

        if db:
            db.close()
