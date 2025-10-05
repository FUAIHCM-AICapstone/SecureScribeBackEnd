
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.schemas.user import MeetingNoteResponse


class MeetingNoteRequest(BaseModel):
    content: Optional[str] = None
    sections: Optional[List[str]] = None


# class MeetingNoteAIResponse(BaseModel):
#     meeting_type: Optional[str] = None
#     is_informative: Optional[bool] = None
#     task_items: List[Dict[str, Any]] = Field(default_factory=list)
#     decision_items: List[Dict[str, Any]] = Field(default_factory=list)
#     question_items: List[Dict[str, Any]] = Field(default_factory=list)
#     token_usage: Dict[str, Any] = Field(default_factory=dict)
#
class MeetingNoteSummaryResponse(BaseModel):
    note: MeetingNoteResponse
    content: str
    summaries: Dict[str, str]
    sections: List[str]
    # ai: Optional[MeetingNoteAIResponse] = None