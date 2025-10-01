import uuid
from typing import Iterable, List, Set

from agno.models.message import Message
from sqlalchemy.orm import Session
from sqlmodel import select

from app.models.chat import ChatMessage, ChatMessageType
from app.models.meeting import MeetingNote, Transcript
from app.models.user import User
from app.services.meeting import get_meeting
from app.utils.llm import get_agno_postgres_db, create_meeting_chat_agent


def get_meeting_transcript(meeting_id: str, db: Session, user_id: uuid.UUID) -> str:
    """Get meeting transcript content."""
    try:
        meeting_uuid = uuid.UUID(meeting_id)
        meeting = get_meeting(db, meeting_uuid, user_id)
        if not meeting:
            return "Meeting not found or access denied."

        transcript = db.exec(
            select(Transcript).where(Transcript.meeting_id == meeting_uuid)
        ).first()
        if not transcript or not transcript.content:
            return "No transcript available for this meeting."

        return f"Meeting: {meeting.title}\nTranscript:\n{transcript.content}"
    except ValueError:
        return "Invalid meeting ID format."
    except Exception as e:
        return f"Error retrieving transcript: {str(e)}"


def get_meeting_notes(meeting_id: str, db: Session, user_id: uuid.UUID) -> str:
    """Get meeting notes content."""
    try:
        meeting_uuid = uuid.UUID(meeting_id)
        meeting = get_meeting(db, meeting_uuid, user_id)
        if not meeting:
            return "Meeting not found or access denied."

        notes = db.exec(
            select(MeetingNote).where(MeetingNote.meeting_id == meeting_uuid)
        ).first()
        if not notes or not notes.content:
            return "No notes available for this meeting."

        return f"Meeting: {meeting.title}\nNotes:\n{notes.content}"
    except ValueError:
        return "Invalid meeting ID format."
    except Exception as e:
        return f"Error retrieving notes: {str(e)}"


def get_meeting_metadata(meeting_id: str, db: Session, user_id: uuid.UUID) -> str:
    """Get meeting metadata and details."""
    try:
        meeting_uuid = uuid.UUID(meeting_id)
        meeting = get_meeting(db, meeting_uuid, user_id)
        if not meeting:
            return "Meeting not found or access denied."

        creator = db.exec(select(User).where(User.id == meeting.created_by)).first()

        import textwrap

        return textwrap.dedent(
            f"""\
            Meeting Details:
            - Title: {meeting.title or "Untitled"}
            - Description: {meeting.description or "No description"}
            - Status: {meeting.status}
            - Start Time: {meeting.start_time or "Not scheduled"}
            - Created By: {creator.name if creator else "Unknown"}
            - Created At: {meeting.created_at}
            - Meeting URL: {meeting.url or "No URL"}
            - Personal Meeting: {"Yes" if meeting.is_personal else "No"}"""
        )
    except ValueError:
        return "Invalid meeting ID format."
    except Exception as e:
        return f"Error retrieving metadata: {str(e)}"


def get_meeting_chat_agent(
    db: Session, user_id: uuid.UUID, meeting_id: uuid.UUID, session_id: str
):
    """Factory function to create a meeting chat agent."""
    try:
        meeting = get_meeting(db, meeting_id, user_id)
        if not meeting:
            return None

        agno_db = get_agno_postgres_db()

        # Define tools as named functions (NOT lambdas)
        def meeting_transcript_tool(mid: str = str(meeting_id)) -> str:
            return get_meeting_transcript(mid, db, user_id)

        def meeting_notes_tool(mid: str = str(meeting_id)) -> str:
            return get_meeting_notes(mid, db, user_id)

        def meeting_metadata_tool(mid: str = str(meeting_id)) -> str:
            return get_meeting_metadata(mid, db, user_id)

        tools: List = [
            meeting_transcript_tool,
            meeting_notes_tool,
            meeting_metadata_tool,
        ]

        return create_meeting_chat_agent(
            agno_db=agno_db,
            session_id=session_id,
            user_id=str(user_id),
            meeting_id=str(meeting_id),
            meeting_title=meeting.title if meeting else "Unknown",
            tools=tools,
        )
    except Exception as e:
        print(f"Error creating meeting chat agent: {e}")
        return None


def _resolve_message_role(message_type: str) -> str:
    if isinstance(message_type, ChatMessageType):
        value = message_type.value
    else:
        value = str(message_type)
    if value == ChatMessageType.agent.value:
        return "assistant"
    if value == ChatMessageType.system.value:
        return "system"
    return "user"


def prime_agent_with_history(agent, history: Iterable[ChatMessage]) -> None:
    if not agent:
        return
    buffered = list(history)
    if not buffered:
        return
    seen: Set[str] = set(getattr(agent, "_secure_scribe_seen_message_ids", set()))
    fresh = [message for message in buffered if str(message.id) not in seen and message.content]
    if not fresh:
        return
    agno_messages = [Message(role=_resolve_message_role(message.message_type), content=message.content) for message in fresh]
    if not agno_messages:
        return
    updated = False
    memory = getattr(agent, "memory", None)
    if memory:
        if hasattr(memory, "add_messages"):
            try:
                memory.add_messages(agno_messages)
                updated = True
            except Exception:
                pass
        elif hasattr(memory, "add"):
            try:
                for msg in agno_messages:
                    memory.add(msg)
                updated = True
            except Exception:
                pass
    if not updated:
        if hasattr(agent, "add_messages"):
            try:
                agent.add_messages(agno_messages)
                updated = True
            except Exception:
                pass
        elif hasattr(agent, "add_message"):
            try:
                for msg in agno_messages:
                    agent.add_message(msg)
                updated = True
            except Exception:
                pass
    if not updated and hasattr(agent, "db") and hasattr(agent, "session_id"):
        db = getattr(agent, "db", None)
        session_id = getattr(agent, "session_id", None)
        if db and session_id:
            if hasattr(db, "add_messages"):
                try:
                    db.add_messages(session_id, agno_messages)
                    updated = True
                except Exception:
                    pass
            elif hasattr(db, "add_message"):
                try:
                    for msg in agno_messages:
                        db.add_message(session_id, msg)
                    updated = True
                except Exception:
                    pass
    if updated:
        seen.update(str(message.id) for message in fresh)
        setattr(agent, "_secure_scribe_seen_message_ids", seen)
