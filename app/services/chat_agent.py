import uuid
from typing import List, Optional

from sqlalchemy.orm import Session
from sqlmodel import select

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
