from typing import List

from agno.models.google import Gemini
from agno.models.message import Message
from google import genai

from app.core.config import settings


def _get_client() -> genai.Client:
    return genai.Client(api_key=settings.GOOGLE_API_KEY)


def _get_model() -> Gemini:
    return Gemini(
        id="gemini-2.5-flash",
        api_key=settings.GOOGLE_API_KEY,
    )


async def embed_query(query: str) -> List[float]:
    client = _get_client()
    result = client.models.embed_content(
        model="gemini-embedding-001",
        contents=query
    )
    return result.embeddings[0].values


async def embed_documents(docs: List[str]) -> List[List[float]]:
    if not docs:
        return []
    client = _get_client()
    result = client.models.embed_content(
        model="gemini-embedding-001",
        contents=docs
    )
    return [emb.values for emb in result.embeddings]


async def chat_complete(system_prompt: str, user_prompt: str) -> str:
    model = _get_model()
    messages = [
        Message(role="system", content=system_prompt),
        Message(role="user", content=user_prompt)
    ]
    assistant_message = Message(role="assistant", content="")
    response = await model.ainvoke(messages, assistant_message)
    return response.content
