from typing import List

from agno.models.google import Gemini

from app.core.config import settings


def _get_model() -> Gemini:
    return Gemini(
        id="gemini-2.5-flash",
        api_key=settings.GOOGLE_API_KEY,
    )


async def embed_query(query: str) -> List[float]:
    model = _get_model()
    response = await model.aembed_query(query)
    return response


async def embed_documents(docs: List[str]) -> List[List[float]]:
    if not docs:
        return []
    model = _get_model()
    response = await model.aembed_documents(docs)
    return response


async def chat_complete(system_prompt: str, user_prompt: str) -> str:
    model = _get_model()
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    response = await model.achat(messages)
    return response.content
