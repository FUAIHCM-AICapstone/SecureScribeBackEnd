import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

from sqlalchemy.orm import Session

from app.models.chat import ChatMessage, Conversation
from app.schemas.chat import Mention
from app.services.qdrant_service import (
    query_documents_by_file_id,
    query_documents_by_meeting_id,
    query_documents_by_project_id,
)


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


async def query_documents_for_mentions(mentions: List[Mention], current_user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Query documents based on mentions and return results.
    """
    if not mentions:
        return []

    results = []

    for mention in mentions:
        entity_type = mention.entity_type
        entity_id = mention.entity_id

        if not entity_id:
            continue

        documents: List[dict] = []

        if entity_type == "meeting":
            documents = await query_documents_by_meeting_id(entity_id, top_k=5)
        elif entity_type == "project":
            documents = await query_documents_by_project_id(entity_id, top_k=5)
        elif entity_type == "file":
            documents = await query_documents_by_file_id(entity_id, top_k=5)
        else:
            # Unsupported mention types are ignored
            continue

        if documents:
            results.extend(documents)

    return results


async def perform_query_expansion_search(
    query: str,
    mentions: Optional[List[Mention]] = None,
    top_k: int = 5,
    num_expansions: int = 3,
) -> List[Dict[str, Any]]:
    """
    Orchestrate query expansion and semantic search.
    
    Args:
        query: Original user query
        mentions: Optional list of mentions to filter by
        top_k: Number of results to return
        num_expansions: Number of expanded queries to generate
        
    Returns:
        List of unique documents sorted by score
    """
    try:
        from app.utils.llm import expand_query_with_llm
        from app.services.qdrant_service import semantic_search_with_filters
        
        print(f"🔍 \033[94mStarting query expansion search for: '{query[:50]}...'\033[0m")
        
        # Generate expanded queries
        expanded_queries = await expand_query_with_llm(query, num_expansions)
        print(f"🟢 \033[92mExpanded into {len(expanded_queries)} queries\033[0m")
        
        # Extract filters from mentions
        meeting_ids = []
        project_ids = []
        file_ids = []
        
        if mentions:
            for mention in mentions:
                if not mention.entity_id:
                    continue
                    
                if mention.entity_type == "meeting":
                    meeting_ids.append(mention.entity_id)
                elif mention.entity_type == "project":
                    project_ids.append(mention.entity_id)
                elif mention.entity_type == "file":
                    file_ids.append(mention.entity_id)
        
        # Perform semantic search for each expanded query
        all_results = []
        for idx, expanded_query in enumerate(expanded_queries):
            print(f"🔎 \033[96mSearching with query {idx+1}/{len(expanded_queries)}: '{expanded_query[:50]}...'\033[0m")
            
            results = await semantic_search_with_filters(
                query=expanded_query,
                top_k=top_k,
                meeting_ids=meeting_ids if meeting_ids else None,
                project_ids=project_ids if project_ids else None,
                file_ids=file_ids if file_ids else None,
            )
            
            all_results.extend(results)
        
        # Deduplicate by document id, keeping highest score
        seen_ids: Dict[str, Dict[str, Any]] = {}
        for doc in all_results:
            doc_id = doc["id"]
            if doc_id not in seen_ids or doc["score"] > seen_ids[doc_id]["score"]:
                seen_ids[doc_id] = doc
        
        # Sort by score and return top_k
        deduplicated_results = list(seen_ids.values())
        deduplicated_results.sort(key=lambda x: x["score"], reverse=True)
        final_results = deduplicated_results[:top_k]
        
        print(f"🟢 \033[92mQuery expansion search completed: {len(final_results)} unique documents\033[0m")
        return final_results
        
    except Exception as e:
        print(f"🔴 \033[91mQuery expansion search failed: {e}\033[0m")
        return []
