import textwrap
from typing import List, Optional

from agno.agent import Agent
from agno.db.postgres import PostgresDb
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


def get_agno_postgres_db() -> PostgresDb:
    """Get agno PostgresDb instance for session management"""
    kwargs = {
        "db_url": str(settings.SQLALCHEMY_DATABASE_URI),
        "session_table": "agno_sessions",
    }
    try:
        return PostgresDb(**kwargs, user_memory_table="agno_user_memories")
    except TypeError:
        return PostgresDb(**kwargs)


def create_chat_agent(
    agno_db: PostgresDb,
    session_id: str,
    user_id: str,
    tools: Optional[List] = None,
    agent_name: str = "SecureScribe Assistant",
) -> Agent:
    """Create a generic chat agent that can leverage mention context."""
    tools = tools or []
    description = textwrap.dedent(
        f"""
        You are a helpful AI assistant supporting SecureScribe chat sessions.

        Conversation context:
        - User ID: {user_id}
        - Session ID: {session_id}

        Guidance:
        - Use provided tools (such as mention_context_tool) to interpret references like @project or @meeting tokens when available.
        - Base your responses on conversation history and resolved context.
        - If context is missing for a mention, acknowledge the gap instead of inventing details.
        - Respond clearly and concisely, using markdown when helpful.
        """
    ).strip()

    return Agent(
        name=agent_name,
        model=_get_model(),
        db=agno_db,
        session_id=session_id,
        user_id=user_id,
        tools=tools,
        enable_user_memories=True,
        enable_session_summaries=True,
        add_history_to_context=True,
        num_history_runs=5,
        markdown=True,
        description=description,
    )
