import uuid
from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.chat import ChatMessage, Conversation
from app.schemas.chat import Mention
from app.services.qdrant_service import query_documents_by_meeting_id


def create_chat_message(db: Session, conversation_id: uuid.UUID, user_id: uuid.UUID, content: str, message_type: str, mentions: Optional[List] = None) -> Optional[ChatMessage]:
    """Create a chat message"""
    # Verify conversation exists and user has access
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id, Conversation.user_id == user_id, Conversation.is_active == True).first()

    if not conversation:
        return None

    # Ensure mentions are serializable dictionaries
    serializable_mentions = None
    if mentions:
        serializable_mentions = []
        for mention in mentions:
            if hasattr(mention, "dict"):
                # Convert Pydantic model to dict
                serializable_mentions.append(mention.dict())
            elif isinstance(mention, dict):
                # Already a dict
                serializable_mentions.append(mention)
            else:
                # Convert to dict if it's a simple object
                serializable_mentions.append(dict(mention))

    db_message = ChatMessage(conversation_id=conversation_id, message_type=message_type, content=content, mentions=serializable_mentions)
    db.add(db_message)

    # Update conversation's updated_at timestamp
    conversation.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_message)
    return db_message


async def query_documents_for_mentions(mentions: List[Mention], current_user_id: str = None) -> List[dict]:
    """
    Query documents based on mentions and return results.
    """
    if not mentions:
        return []

    results = []

    for mention in mentions:
        entity_type = mention.entity_type
        entity_id = mention.entity_id

        if entity_type == "meeting":
            # Use existing qdrant service to query
            meeting_docs = await query_documents_by_meeting_id(entity_id, top_k=5)
            results.extend(meeting_docs)

    return results

