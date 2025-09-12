from typing import Any, Dict, List, TypedDict

from langgraph.graph import END, StateGraph

from app.core.config import settings
from app.services.qdrant_service import search_vectors
from app.utils.llm import chat_complete, embed_query


class QAState(TypedDict):
    query: str
    contexts: List[str]
    answer: str
    project_id: str | None
    meeting_id: str | None
    current_user_id: str | None


async def _retrieve_node(state: QAState) -> QAState:
    query = state["query"]
    qvec = await embed_query(query)
    # Build Qdrant filter for scope
    from qdrant_client.http.models import FieldCondition, Filter, MatchValue

    qfilter = None
    if state.get("meeting_id"):
        qfilter = Filter(
            should=[
                FieldCondition(
                    key="meeting_id", match=MatchValue(value=state["meeting_id"])
                ),
                FieldCondition(key="is_global", match=MatchValue(value=True)),
            ],
            must=[
                FieldCondition(
                    key="uploaded_by",
                    match=MatchValue(value=(state.get("current_user_id") or "")),
                ),
            ],
        )
    elif state.get("project_id"):
        qfilter = Filter(
            should=[
                FieldCondition(
                    key="project_id", match=MatchValue(value=state["project_id"])
                ),
                FieldCondition(
                    key="uploaded_by",
                    match=MatchValue(value=(state.get("current_user_id") or "")),
                ),
            ]
        )

    results = await search_vectors(
        collection=settings.QDRANT_COLLECTION_NAME,
        query_vector=qvec,
        top_k=5,
        query_filter=qfilter,
    )
    contexts: List[str] = []
    for r in results:
        payload = getattr(r, "payload", {}) or {}
        text = payload.get("text", "")
        if not text:
            continue

        # Enforce scope locally using payload metadata
        if state.get("meeting_id"):
            if payload.get("meeting_id") == state.get("meeting_id"):
                contexts.append(text)
            continue

        if state.get("project_id"):
            if payload.get("project_id") == state.get("project_id"):
                contexts.append(text)
                continue
            if (
                payload.get("uploaded_by") == state.get("current_user_id")
                and not payload.get("project_id")
                and not payload.get("meeting_id")
            ):
                contexts.append(text)
            continue

        # No explicit scope
        contexts.append(text)
    return {
        "query": query,
        "contexts": contexts,
        "answer": "",
        "project_id": state.get("project_id"),
        "meeting_id": state.get("meeting_id"),
        "current_user_id": state.get("current_user_id"),
    }


async def _generate_node(state: QAState) -> QAState:
    query = state["query"]
    context_text = "\n\n".join(state["contexts"][:5])
    system = "You are a concise assistant. Answer using the provided context only."
    user = f"Context:\n{context_text}\n\nQuestion: {query}"
    answer = await chat_complete(system, user)
    return {
        "query": query,
        "contexts": state["contexts"],
        "answer": answer,
        "project_id": state.get("project_id"),
        "meeting_id": state.get("meeting_id"),
        "current_user_id": state.get("current_user_id"),
    }


_builder = StateGraph(QAState)
_builder.add_node("retrieve", _retrieve_node)
_builder.add_node("generate", _generate_node)
_builder.set_entry_point("retrieve")
_builder.add_edge("retrieve", "generate")
_builder.add_edge("generate", END)
_graph = _builder.compile()


async def run_rag(
    query: str,
    _db: Any | None = None,
    current_user: Any | None = None,
    project_id: str | None = None,
    meeting_id: str | None = None,
) -> Dict[str, Any]:
    """Execute minimal two-step RAG over Qdrant and LLM with scope filtering."""
    state: QAState = {
        "query": query,
        "contexts": [],
        "answer": "",
        "project_id": project_id,
        "meeting_id": meeting_id,
        "current_user_id": str(getattr(current_user, "id", ""))
        if current_user
        else None,
    }
    result: QAState = await _graph.ainvoke(state)
    return {"answer": result["answer"], "contexts": result["contexts"][:5]}
