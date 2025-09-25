import uuid
from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session
from sqlmodel import select

from app.models.chat import ChatMessage, ChatMessageType, ChatSession
from app.models.meeting import Meeting
from app.models.user import User
from app.schemas.chat import ChatSessionCreate, ChatSessionUpdate
from app.services.meeting import get_meeting


def create_chat_session(db: Session, meeting_id: uuid.UUID, user_id: uuid.UUID, chat_data: ChatSessionCreate) -> Optional[ChatSession]:
    """Create a new chat session for a meeting"""
    # Verify user has access to the meeting
    meeting = get_meeting(db, meeting_id, user_id, raise_404=True)
    if not meeting:
        return None

    # Check if user already has an active session for this meeting
    existing_session = db.exec(select(ChatSession).where(ChatSession.meeting_id == meeting_id, ChatSession.user_id == user_id, ChatSession.is_active == True)).first()

    if existing_session:
        return existing_session

    # Generate agno session ID
    agno_session_id = f"meeting_{meeting_id}_{user_id}_{uuid.uuid4().hex[:8]}"

    # Auto-generate title if not provided
    title = chat_data.title or f"Chat about {meeting.title or 'Meeting'}"

    chat_session = ChatSession(meeting_id=meeting_id, user_id=user_id, agno_session_id=agno_session_id, title=title, is_active=True)

    db.add(chat_session)
    db.commit()
    db.refresh(chat_session)

    return chat_session


def get_chat_session(db: Session, session_id: uuid.UUID, user_id: uuid.UUID) -> Optional[ChatSession]:
    """Get a chat session by ID if user has access"""
    return db.exec(select(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == user_id)).first()


def get_chat_sessions_for_meeting(db: Session, meeting_id: uuid.UUID, user_id: uuid.UUID, page: int = 1, limit: int = 20) -> Tuple[List[ChatSession], int]:
    """Get chat sessions for a meeting with pagination"""
    # Verify user has access to meeting
    meeting = get_meeting(db, meeting_id, user_id)
    if not meeting:
        return [], 0

    # Get sessions
    query = select(ChatSession).where(ChatSession.meeting_id == meeting_id, ChatSession.user_id == user_id).order_by(ChatSession.created_at.desc())

    # Count total
    count_query = select(ChatSession).where(ChatSession.meeting_id == meeting_id, ChatSession.user_id == user_id)
    total = len(db.exec(count_query).all())

    # Apply pagination
    offset = (page - 1) * limit
    sessions = db.exec(query.offset(offset).limit(limit)).all()

    return list(sessions), total


def update_chat_session(db: Session, session_id: uuid.UUID, user_id: uuid.UUID, update_data: ChatSessionUpdate) -> Optional[ChatSession]:
    """Update a chat session"""
    session = get_chat_session(db, session_id, user_id)
    if not session:
        return None

    # Update fields
    if update_data.title is not None:
        session.title = update_data.title
    if update_data.is_active is not None:
        session.is_active = update_data.is_active

    session.updated_at = datetime.utcnow()

    db.add(session)
    db.commit()
    db.refresh(session)

    return session


def delete_chat_session(db: Session, session_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    """Delete a chat session and all its messages"""
    session = get_chat_session(db, session_id, user_id)
    if not session:
        return False

    # Delete all messages first
    db.exec(select(ChatMessage).where(ChatMessage.chat_session_id == session_id))
    messages = db.exec(select(ChatMessage).where(ChatMessage.chat_session_id == session_id)).all()

    for message in messages:
        db.delete(message)

    # Delete the session
    db.delete(session)
    db.commit()

    return True


def create_chat_message(db: Session, session_id: uuid.UUID, user_id: uuid.UUID, content: str, message_type: ChatMessageType = ChatMessageType.user, message_metadata: Optional[dict] = None) -> Optional[ChatMessage]:
    """Create a new chat message"""
    # Verify session exists and user has access
    session = get_chat_session(db, session_id, user_id)
    if not session or not session.is_active:
        return None

    message = ChatMessage(chat_session_id=session_id, message_type=message_type, content=content, message_metadata=message_metadata)

    db.add(message)
    db.commit()
    db.refresh(message)

    # Update session timestamp
    session.updated_at = datetime.utcnow()
    db.add(session)
    db.commit()

    return message


def get_chat_messages(db: Session, session_id: uuid.UUID, user_id: uuid.UUID, page: int = 1, limit: int = 50) -> Tuple[List[ChatMessage], int]:
    """Get chat messages for a session with pagination"""
    # Verify session access
    session = get_chat_session(db, session_id, user_id)
    if not session:
        return [], 0

    # Get messages ordered by creation time
    query = select(ChatMessage).where(ChatMessage.chat_session_id == session_id).order_by(ChatMessage.created_at.asc())

    # Count total
    count_query = select(ChatMessage).where(ChatMessage.chat_session_id == session_id)
    total = len(db.exec(count_query).all())

    # Apply pagination
    offset = (page - 1) * limit
    messages = db.exec(query.offset(offset).limit(limit)).all()

    return list(messages), total


def get_chat_session_with_messages(db: Session, session_id: uuid.UUID, user_id: uuid.UUID, message_limit: int = 50) -> Optional[dict]:
    """Get chat session with its messages and meeting info"""
    session = get_chat_session(db, session_id, user_id)
    if not session:
        return None

    # Get messages
    messages, total_messages = get_chat_messages(db, session_id, user_id, limit=message_limit)

    # Get meeting info
    meeting = db.exec(select(Meeting).where(Meeting.id == session.meeting_id)).first()

    return {"session": session, "messages": messages, "total_messages": total_messages, "meeting_title": meeting.title if meeting else None}
