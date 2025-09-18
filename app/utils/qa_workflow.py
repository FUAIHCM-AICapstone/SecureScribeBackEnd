from typing import Any, Dict, List

from app.core.config import settings
from app.services.qdrant_service import search_vectors
from app.utils.llm import chat_complete, embed_query


async def run_rag(
    query: str,
    _db: Any | None = None,
    current_user: Any | None = None,
    project_id: str | None = None,
    meeting_id: str | None = None,
) -> Dict[str, Any]:
    # Get embedding for query
    qvec = await embed_query(query)

    from qdrant_client.http.models import FieldCondition, Filter, MatchValue

    # Build filter based on scope
    qfilter = None
    current_user_id = str(getattr(current_user, "id", "")) if current_user else None

    if meeting_id:
        qfilter = Filter(
            should=[
                FieldCondition(key="meeting_id", match=MatchValue(value=meeting_id)),
                FieldCondition(key="is_global", match=MatchValue(value=True)),
            ],
            must=[FieldCondition(key="uploaded_by", match=MatchValue(value=current_user_id or ""))],
        )
    elif project_id:
        qfilter = Filter(
            should=[
                FieldCondition(key="project_id", match=MatchValue(value=project_id)),
                FieldCondition(key="uploaded_by", match=MatchValue(value=current_user_id or "")),
            ]
        )

    # Search for relevant documents
    results = await search_vectors(
        collection=settings.QDRANT_COLLECTION_NAME,
        query_vector=qvec,
        top_k=5,
        query_filter=qfilter,
    )

    # Extract contexts with filtering
    contexts: List[str] = []
    for r in results:
        payload = getattr(r, "payload", {}) or {}
        text = payload.get("text", "")
        if not text:
            continue

        # Apply additional filtering logic
        should_include = True

        if meeting_id and payload.get("meeting_id") != meeting_id:
            should_include = False

        if project_id:
            if payload.get("project_id") == project_id:
                should_include = True
            elif payload.get("uploaded_by") == current_user_id and not payload.get("project_id") and not payload.get("meeting_id"):
                should_include = True
            else:
                should_include = False

        if should_include:
            contexts.append(text)

    # Generate answer using retrieved context
    context_text = "\n\n".join(contexts[:5])
    system_prompt = "You are a helpful assistant. Answer questions using only the provided context. Be concise and accurate."
    user_prompt = f"Context:\n{context_text}\n\nQuestion: {query}"

    answer = await chat_complete(system_prompt, user_prompt)

    return {"answer": answer, "contexts": contexts[:5]}
