import textwrap
from typing import List

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

# def get_agno_postgres_db() -> PostgresDb:
#     """Get agno PostgresDb instance for session management"""
#     return PostgresDb(db_url=str(settings.SQLALCHEMY_DATABASE_URI), session_table="agno_sessions", user_memory_table="agno_user_memories")

def get_agno_postgres_db() -> PostgresDb:
    """Get agno PostgresDb instance for session management"""
    kwargs = {
        "db_url": str(settings.SQLALCHEMY_DATABASE_URI),
        "session_table": "agno_sessions",
    }
    try:
        return PostgresDb(**kwargs, user_memory_table="agno_user_memories")
    except TypeError:
        # Fallback n???u version khA'ng h??- tr??? user_memory_table
        return PostgresDb(**kwargs)

def create_meeting_chat_agent(agno_db: PostgresDb, session_id: str, user_id: str, meeting_id: str, meeting_title: str, tools: List, agent_name: str = "Meeting Assistant") -> Agent:
    """Create a meeting chat agent with proper configuration"""
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
        description=textwrap.dedent(f"""\
            You are a helpful AI assistant for discussing meeting content.

            Current meeting context:
            - Meeting: {meeting_title or "Unknown"}
            - Meeting ID: {meeting_id}

            You have access to these tools:
            - meeting_transcript_tool: Get meeting transcript from audio recordings
            - meeting_notes_tool: Get user-editable meeting notes
            - meeting_metadata_tool: Get meeting details and metadata
            - meeting_summary_tool: Generate targeted summaries (Objective, Discussion, Decision, Action Items)

            Guidelines:
            - Help users understand and analyze meeting content
            - Answer questions about what was discussed
            - Identify key points, decisions, and action items
            - Provide focused summaries by calling meeting_summary_tool when users ask for overall or section-specific recaps
            - Be conversational and helpful
            - Always base your responses on the actual meeting content
            - Use the appropriate tool to retrieve meeting information when needed
            - Be clear about what information comes from transcripts vs. notes vs. metadata vs. summaries
            - For the current meeting, use meeting ID: {meeting_id}
        """),
    )
