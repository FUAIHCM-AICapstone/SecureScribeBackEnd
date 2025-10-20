from typing import Dict, List, Optional

from pydantic import BaseModel

from app.schemas.user import MeetingNoteResponse


class MeetingNoteRequest(BaseModel):
    content: Optional[str] = None
    sections: Optional[List[str]] = None


class MeetingNoteSummaryResponse(BaseModel):
    note: MeetingNoteResponse
    content: str
    summaries: Dict[str, str]
    sections: List[str]
