import uuid
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.crud.conversation import (
    crud_create_conversation,
    crud_delete_conversation,
    crud_get_conversation,
    crud_get_conversation_with_messages,
    crud_get_conversations_for_user,
    crud_update_conversation,
)
from app.models.chat import Conversation
from app.schemas.conversation import ConversationCreate, ConversationUpdate


def create_conversation(db: Session, user_id: uuid.UUID, conversation_data: ConversationCreate) -> Conversation:
    return crud_create_conversation(db, user_id, conversation_data)


def get_conversations_for_user(db: Session, user_id: uuid.UUID, page: int = 1, limit: int = 20) -> Tuple[List[Conversation], int]:
    return crud_get_conversations_for_user(db, user_id, page, limit)


def get_conversation(db: Session, conversation_id: uuid.UUID, user_id: uuid.UUID) -> Optional[Conversation]:
    return crud_get_conversation(db, conversation_id, user_id)


def get_conversation_with_messages(db: Session, conversation_id: uuid.UUID, user_id: uuid.UUID, limit: int = 50) -> Optional[Conversation]:
    return crud_get_conversation_with_messages(db, conversation_id, user_id, limit)


def update_conversation(db: Session, conversation_id: uuid.UUID, user_id: uuid.UUID, update_data: ConversationUpdate) -> Optional[Conversation]:
    return crud_update_conversation(db, conversation_id, user_id, update_data)


def delete_conversation(db: Session, conversation_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    return crud_delete_conversation(db, conversation_id, user_id)


def check_conversation_active(db: Session, conversation_id: uuid.UUID) -> bool:
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id, Conversation.is_active == True).first()
    return conversation is not None
