from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel

from app.schemas.user import MeetingNoteResponse


class MeetingNoteRequest(BaseModel):
    content: str


class MeetingNoteSummaryResponse(BaseModel):
    note: MeetingNoteResponse
    content: str
    task_items: List[Dict[str, Any]] = []
    decision_items: List[Dict[str, Any]] = []
    question_items: List[Dict[str, Any]] = []
    token_usage: Dict[str, Any] = {}
