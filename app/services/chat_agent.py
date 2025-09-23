import uuid
from typing import Any, Dict, List, Optional

from agno.agent import Agent
from agno.db.postgres import PostgresDb
from agno.models.openai import OpenAIChat
from sqlalchemy.orm import Session
from sqlmodel import select

from app.core.config import settings
from app.models.meeting import Meeting, MeetingNote, Transcript
from app.models.user import User
from app.services.meeting import get_meeting


def get_meeting_transcript(meeting_id: str, db: Session, user_id: uuid.UUID) -> str:
    """Get meeting transcript content
    
    Args:
        meeting_id: The meeting ID to get transcript for
        db: Database session
        user_id: User ID for access control
        
    Returns:
        str: Meeting transcript content or error message
    """
    try:
        meeting_uuid = uuid.UUID(meeting_id)
        
        # Check if user has access to meeting
        meeting = get_meeting(db, meeting_uuid, user_id)
        if not meeting:
            return "Meeting not found or access denied."
        
        # Get transcript
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
    """Get meeting notes content
    
    Args:
        meeting_id: The meeting ID to get notes for
        db: Database session  
        user_id: User ID for access control
        
    Returns:
        str: Meeting notes content or error message
    """
    try:
        meeting_uuid = uuid.UUID(meeting_id)
        
        # Check if user has access to meeting
        meeting = get_meeting(db, meeting_uuid, user_id)
        if not meeting:
            return "Meeting not found or access denied."
        
        # Get notes
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
    """Get meeting metadata and details
    
    Args:
        meeting_id: The meeting ID to get metadata for
        db: Database session
        user_id: User ID for access control
        
    Returns:
        str: Meeting metadata or error message
    """
    try:
        meeting_uuid = uuid.UUID(meeting_id)
        
        # Check if user has access to meeting
        meeting = get_meeting(db, meeting_uuid, user_id)
        if not meeting:
            return "Meeting not found or access denied."
        
        # Get creator info
        creator = db.exec(
            select(User).where(User.id == meeting.created_by)
        ).first()
        
        metadata = f"""Meeting Details:
- Title: {meeting.title or 'Untitled'}
- Description: {meeting.description or 'No description'}
- Status: {meeting.status}
- Start Time: {meeting.start_time or 'Not scheduled'}
- Created By: {creator.name if creator else 'Unknown'}
- Created At: {meeting.created_at}
- Meeting URL: {meeting.url or 'No URL'}
- Personal Meeting: {'Yes' if meeting.is_personal else 'No'}"""
        
        return metadata
        
    except ValueError:
        return "Invalid meeting ID format."
    except Exception as e:
        return f"Error retrieving metadata: {str(e)}"


class MeetingChatAgent:
    """Agent for chatting about meeting content using agno"""
    
    def __init__(self, db: Session, user_id: uuid.UUID, meeting_id: uuid.UUID, session_id: str):
        self.db = db
        self.user_id = user_id
        self.meeting_id = meeting_id
        self.session_id = session_id
        
        # Create agno database connection
        self.agno_db = PostgresDb(
            db_url=str(settings.SQLALCHEMY_DATABASE_URI),
            session_table="agno_sessions",
            user_memory_table="agno_user_memories"
        )
        
        # Get meeting info for context
        self.meeting = get_meeting(db, meeting_id, user_id)
        
        # Create tool functions with closure to capture context
        def meeting_transcript_tool(meeting_id: str) -> str:
            """Get the transcript content for a meeting"""
            return get_meeting_transcript(meeting_id, db, user_id)
        
        def meeting_notes_tool(meeting_id: str) -> str:
            """Get the notes content for a meeting"""
            return get_meeting_notes(meeting_id, db, user_id)
        
        def meeting_metadata_tool(meeting_id: str) -> str:
            """Get metadata and details for a meeting"""
            return get_meeting_metadata(meeting_id, db, user_id)
        
        # Create agent with tools
        self.agent = Agent(
            name="Meeting Assistant",
            model=OpenAIChat(id="gpt-4o"),
            db=self.agno_db,
            session_id=session_id,
            user_id=str(user_id),
            tools=[meeting_transcript_tool, meeting_notes_tool, meeting_metadata_tool],
            enable_user_memories=True,
            enable_session_summaries=True,
            add_history_to_context=True,
            num_history_runs=5,
            markdown=True,
            description=f"""You are a helpful AI assistant for discussing meeting content.

Current meeting context:
- Meeting: {self.meeting.title if self.meeting else 'Unknown'}
- Meeting ID: {meeting_id}

You have access to these tools:
- meeting_transcript_tool: Get meeting transcript from audio recordings
- meeting_notes_tool: Get user-editable meeting notes
- meeting_metadata_tool: Get meeting details and metadata

Guidelines:
- Help users understand and analyze meeting content
- Answer questions about what was discussed
- Identify key points, decisions, and action items
- Be conversational and helpful
- Always base your responses on the actual meeting content
- Use the appropriate tool to retrieve meeting information when needed
- Be clear about what information comes from transcripts vs. notes vs. metadata
- For the current meeting, use meeting ID: {meeting_id}"""
        )
    
    def chat(self, message: str) -> str:
        """Send a message to the agent and get response"""
        try:
            response = self.agent.run(message)
            return response.content if hasattr(response, 'content') else str(response)
        except Exception as e:
            return f"I apologize, but I encountered an error: {str(e)}"
    
    async def chat_async(self, message: str) -> str:
        """Send a message to the agent asynchronously and get response"""
        try:
            response = await self.agent.arun(message)
            return response.content if hasattr(response, 'content') else str(response)
        except Exception as e:
            return f"I apologize, but I encountered an error: {str(e)}"
    
    def get_session_info(self) -> Dict[str, Any]:
        """Get information about the current session"""
        return {
            "session_id": self.session_id,
            "user_id": str(self.user_id),
            "meeting_id": str(self.meeting_id),
            "meeting_title": self.meeting.title if self.meeting else None,
            "tools_available": ["meeting_transcript_tool", "meeting_notes_tool", "meeting_metadata_tool"]
        }


def create_meeting_chat_agent(
    db: Session, 
    user_id: uuid.UUID, 
    meeting_id: uuid.UUID, 
    session_id: str
) -> Optional[MeetingChatAgent]:
    """Factory function to create a meeting chat agent"""
    try:
        # Verify user has access to meeting
        meeting = get_meeting(db, meeting_id, user_id)
        if not meeting:
            return None
        
        return MeetingChatAgent(db, user_id, meeting_id, session_id)
    
    except Exception as e:
        print(f"Error creating meeting chat agent: {e}")
        return None
