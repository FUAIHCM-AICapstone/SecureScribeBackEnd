import uuid
from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.chat import ChatMessage, Conversation
from app.schemas.conversation import ConversationCreate, ConversationUpdate


def create_conversation(db: Session, user_id: uuid.UUID, conversation_data: ConversationCreate) -> Conversation:
    """Create a new conversation for a user"""
    db_conversation = Conversation(
        user_id=user_id,
        agno_session_id=f"conv_{uuid.uuid4()}",
        title=conversation_data.title,
    )
    db.add(db_conversation)
    db.commit()
    db.refresh(db_conversation)
    return db_conversation


def get_conversations_for_user(db: Session, user_id: uuid.UUID, page: int = 1, limit: int = 20) -> Tuple[List[Conversation], int]:
    """Get conversations for a user with pagination"""
    query = db.query(Conversation).filter(Conversation.user_id == user_id, Conversation.is_active == True).order_by(Conversation.updated_at.desc())

    total = query.count()
    conversations = query.offset((page - 1) * limit).limit(limit).all()

    return conversations, total


def get_conversation(db: Session, conversation_id: uuid.UUID, user_id: uuid.UUID) -> Optional[Conversation]:
    """Get a specific conversation if user has access"""
    return db.query(Conversation).filter(Conversation.id == conversation_id, Conversation.user_id == user_id, Conversation.is_active == True).first()


def get_conversation_with_messages(db: Session, conversation_id: uuid.UUID, user_id: uuid.UUID, limit: int = 50) -> Optional[Conversation]:
    """Get a conversation with its messages"""
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id, Conversation.user_id == user_id, Conversation.is_active == True).first()

    if not conversation:
        return None

    # Load messages
    messages = db.query(ChatMessage).filter(ChatMessage.conversation_id == conversation_id).order_by(ChatMessage.created_at.asc()).limit(limit).all()

    conversation.messages = messages
    return conversation


def update_conversation(db: Session, conversation_id: uuid.UUID, user_id: uuid.UUID, update_data: ConversationUpdate) -> Optional[Conversation]:
    """Update a conversation"""
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id, Conversation.user_id == user_id, Conversation.is_active == True).first()

    if not conversation:
        return None

    # Update fields
    if update_data.title is not None:
        conversation.title = update_data.title
    if update_data.is_active is not None:
        conversation.is_active = update_data.is_active

    conversation.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(conversation)
    return conversation


def delete_conversation(db: Session, conversation_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    """Soft delete a conversation by setting is_active to False"""
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id, Conversation.user_id == user_id).first()

    if not conversation:
        return False

    conversation.is_active = False
    conversation.updated_at = datetime.utcnow()
    db.commit()
    return True
