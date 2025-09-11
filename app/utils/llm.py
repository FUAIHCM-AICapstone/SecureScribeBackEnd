from typing import List

import google.generativeai as genai

from app.core.config import settings


def init_google_ai():
    """Initialize Google AI client"""
    genai.configure(api_key=settings.GOOGLE_API_KEY)
    return genai


def get_embedding_client():
    """Get Google AI embedding client"""
    return init_google_ai()


async def embed_query(query: str) -> List[float]:
    """Generate embedding for query"""
    client = get_embedding_client()
    result = client.embed_content(
        model="models/text-embedding-004",
        content=query,
        task_type="retrieval_query",
    )
    return result["embedding"] if result and "embedding" in result else []


async def embed_documents(docs: List[str]) -> List[List[float]]:
    """Generate embeddings for documents"""
    if not docs:
        return []

    client = get_embedding_client()
    embeddings = []

    for doc in docs:
        result = client.embed_content(
            model="models/text-embedding-004",
            content=doc,
            task_type="retrieval_document",
        )
        if result and "embedding" in result:
            embeddings.append(result["embedding"])

    return embeddings
