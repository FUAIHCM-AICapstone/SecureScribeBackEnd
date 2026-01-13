import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.chat import ChatMessage, Conversation


def crud_create_chat_message(db: Session, conversation_id: uuid.UUID, user_id: uuid.UUID, content: str, message_type: str, mentions: Optional[List] = None) -> Optional[ChatMessage]:
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id, Conversation.user_id == user_id, Conversation.is_active == True).first()

    if not conversation:
        return None

    serializable_mentions = None
    if mentions:
        serializable_mentions = []
        for mention in mentions:
            if hasattr(mention, "dict"):
                serializable_mentions.append(mention.dict())
            elif isinstance(mention, dict):
                serializable_mentions.append(mention)
            else:
                serializable_mentions.append(dict(mention))

    db_message = ChatMessage(conversation_id=conversation_id, message_type=message_type, content=content, mentions=serializable_mentions)
    db.add(db_message)

    conversation.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(db_message)
    return db_message
