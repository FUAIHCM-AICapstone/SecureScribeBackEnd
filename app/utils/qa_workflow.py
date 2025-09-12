from typing import Any, Dict, List, TypedDict

from agno.workflow.v2 import Step, StepOutput, Workflow

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


async def retrieve_step(step_input: Dict[str, Any]) -> StepOutput:
    state: QAState = step_input["state"]
    query = state["query"]
    qvec = await embed_query(query)

    from qdrant_client.http.models import FieldCondition, Filter, MatchValue

    qfilter = None
    if state.get("meeting_id"):
        qfilter = Filter(
            should=[
                FieldCondition(key="meeting_id", match=MatchValue(value=state["meeting_id"])),
                FieldCondition(key="is_global", match=MatchValue(value=True)),
            ],
            must=[
                FieldCondition(
                    key="uploaded_by", match=MatchValue(value=(state.get("current_user_id") or ""))
                )
            ],
        )
    elif state.get("project_id"):
        qfilter = Filter(
            should=[
                FieldCondition(key="project_id", match=MatchValue(value=state["project_id"])),
                FieldCondition(key="uploaded_by", match=MatchValue(value=(state.get("current_user_id") or ""))),
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

        contexts.append(text)

    state["contexts"] = contexts
    return StepOutput(output=state)


async def generate_step(step_input: Dict[str, Any]) -> StepOutput:
    state: QAState = step_input["state"]
    query = state["query"]
    context_text = "\n\n".join(state["contexts"][:5])
    system = "You are a concise assistant. Answer using the provided context only."
    user = f"Context:\n{context_text}\n\nQuestion: {query}"
    answer = await chat_complete(system, user)
    state["answer"] = answer
    return StepOutput(output=state)


workflow = Workflow(
    name="RAGWorkflow",
    steps=[
        Step("retrieve", retrieve_step),
        Step("generate", generate_step, depends_on=["retrieve"]),
    ],
)


async def run_rag(
    query: str,
    _db: Any | None = None,
    current_user: Any | None = None,
    project_id: str | None = None,
    meeting_id: str | None = None,
) -> Dict[str, Any]:
    state: QAState = {
        "query": query,
        "contexts": [],
        "answer": "",
        "project_id": project_id,
        "meeting_id": meeting_id,
        "current_user_id": str(getattr(current_user, "id", "")) if current_user else None,
    }
    result = await workflow.arun(initial_input={"state": state})
    final_state: QAState = result.output
    return {"answer": final_state["answer"], "contexts": final_state["contexts"][:5]}
