import uuid
from datetime import datetime
from typing import List, Optional, Set, Tuple

from sqlalchemy.orm import Session
from sqlmodel import select

from app.models.chat import ChatMessage, ChatMessageType, ChatSession
from app.schemas.chat import ChatSessionCreate, ChatSessionUpdate


def create_chat_session(
    db: Session, user_id: uuid.UUID, chat_data: ChatSessionCreate
) -> Optional[ChatSession]:
    """Create a new chat session for a user."""
    title = chat_data.title or "New chat session"

    agno_session_id = f"user_{user_id}_{uuid.uuid4().hex[:8]}"

    chat_session = ChatSession(
        user_id=user_id,
        agno_session_id=agno_session_id,
        title=title,
        is_active=True,
    )

    db.add(chat_session)
    db.commit()
    db.refresh(chat_session)

    return chat_session


def get_chat_session(
    db: Session, session_id: uuid.UUID, user_id: uuid.UUID
) -> Optional[ChatSession]:
    """Get a chat session by ID if user has access."""
    return db.exec(
        select(ChatSession).where(
            ChatSession.id == session_id, ChatSession.user_id == user_id
        )
    ).first()


def get_chat_sessions_for_user(
    db: Session, user_id: uuid.UUID, page: int = 1, limit: int = 20
) -> Tuple[List[ChatSession], int]:
    """Get chat sessions for a user with pagination."""
    query = (
        select(ChatSession)
        .where(ChatSession.user_id == user_id)
        .order_by(ChatSession.created_at.desc())
    )

    count_query = select(ChatSession).where(ChatSession.user_id == user_id)
    total = len(db.exec(count_query).all())

    offset = (page - 1) * limit
    sessions = db.exec(query.offset(offset).limit(limit)).all()

    return list(sessions), total


def update_chat_session(
    db: Session, session_id: uuid.UUID, user_id: uuid.UUID, update_data: ChatSessionUpdate
) -> Optional[ChatSession]:
    """Update a chat session."""
    session = get_chat_session(db, session_id, user_id)
    if not session:
        return None

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
    """Delete a chat session and all its messages."""
    session = get_chat_session(db, session_id, user_id)
    if not session:
        return False

    messages = db.exec(
        select(ChatMessage).where(ChatMessage.chat_session_id == session_id)
    ).all()

    for message in messages:
        db.delete(message)

    db.delete(session)
    db.commit()

    return True


def create_chat_message(
    db: Session,
    session_id: uuid.UUID,
    user_id: uuid.UUID,
    content: str,
    message_type: ChatMessageType = ChatMessageType.user,
    message_metadata: Optional[dict] = None,
    mentions: Optional[List[dict]] = None,
) -> Optional[ChatMessage]:
    """Create a new chat message."""
    session = get_chat_session(db, session_id, user_id)
    if not session or not session.is_active:
        return None

    message = ChatMessage(
        chat_session_id=session_id,
        message_type=message_type,
        content=content,
        message_metadata=message_metadata,
        mentions=mentions or [],
    )

    db.add(message)
    db.commit()
    db.refresh(message)

    session.updated_at = datetime.utcnow()
    db.add(session)
    db.commit()

    return message


def get_chat_messages(
    db: Session, session_id: uuid.UUID, user_id: uuid.UUID, page: int = 1, limit: int = 50
) -> Tuple[List[ChatMessage], int]:
    """Get chat messages for a session with pagination."""
    session = get_chat_session(db, session_id, user_id)
    if not session:
        return [], 0

    query = (
        select(ChatMessage)
        .where(ChatMessage.chat_session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
    )

    count_query = select(ChatMessage).where(ChatMessage.chat_session_id == session_id)
    total = len(db.exec(count_query).all())

    offset = (page - 1) * limit
    messages = db.exec(query.offset(offset).limit(limit)).all()

    return list(messages), total


def get_chat_history(
    db: Session,
    session_id: uuid.UUID,
    user_id: uuid.UUID,
    limit: int = 50,
    exclude_message_ids: Optional[Set[uuid.UUID]] = None,
) -> List[ChatMessage]:
    """Get ordered chat history limited to recent messages."""
    session = get_chat_session(db, session_id, user_id)
    if not session:
        return []

    limit = max(limit, 1)
    query = (
        select(ChatMessage)
        .where(ChatMessage.chat_session_id == session_id)
        .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
        .limit(limit)
    )
    messages = list(db.exec(query).all())[::-1]

    if not messages:
        return []

    if exclude_message_ids:
        excluded = set(exclude_message_ids)
        messages = [message for message in messages if message.id not in excluded]

    return messages


def get_chat_session_with_messages(
    db: Session, session_id: uuid.UUID, user_id: uuid.UUID, message_limit: int = 50
) -> Optional[dict]:
    """Get chat session with its messages."""
    session = get_chat_session(db, session_id, user_id)
    if not session:
        return None

    messages, total_messages = get_chat_messages(
        db, session_id, user_id, limit=message_limit
    )

    return {
        "session": session,
        "messages": messages,
        "total_messages": total_messages,
    }
