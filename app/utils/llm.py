from typing import List

from agno.models.google import Gemini
from agno.models.message import Message
from chonkie import GeminiEmbeddings

from app.core.config import settings


def _get_model() -> Gemini:
    return Gemini(
        id="gemini-2.5-flash",
        api_key=settings.GOOGLE_API_KEY,
    )


def _get_embeddings() -> GeminiEmbeddings:
    return GeminiEmbeddings(api_key=settings.GOOGLE_API_KEY)


async def embed_query(query: str) -> List[float]:
    embeddings = _get_embeddings()
    vector = embeddings.embed(query)
    return list(vector)


async def embed_documents(docs: List[str]) -> List[List[float]]:
    if not docs:
        return []
    embeddings = _get_embeddings()
    vectors = embeddings.embed_batch(docs)
    return [list(v) for v in vectors]


async def chat_complete(system_prompt: str, user_prompt: str) -> str:
    model = _get_model()
    messages = [
        Message(role="system", content=system_prompt),
        Message(role="user", content=user_prompt),
    ]
    assistant_message = Message(role="assistant", content="")
    response = await model.ainvoke(messages, assistant_message)
    return response.content
