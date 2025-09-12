from typing import List

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import (
    ChatGoogleGenerativeAI,
    GoogleGenerativeAIEmbeddings,
)

from app.core.config import settings


def _get_embedder() -> GoogleGenerativeAIEmbeddings:
    return GoogleGenerativeAIEmbeddings(
        model="models/text-embedding-004",
        google_api_key=settings.GOOGLE_API_KEY,
    )


def _get_chat_model() -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model="gemini-1.5-flash",
        google_api_key=settings.GOOGLE_API_KEY,
        temperature=0.2,
    )


async def embed_query(query: str) -> List[float]:
    embedder = _get_embedder()
    return embedder.embed_query(query)


async def embed_documents(docs: List[str]) -> List[List[float]]:
    if not docs:
        return []
    embedder = _get_embedder()
    return embedder.embed_documents(docs)


async def chat_complete(system_prompt: str, user_prompt: str) -> str:
    llm = _get_chat_model()
    resp = llm.invoke(
        [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
    )
    return resp.content
