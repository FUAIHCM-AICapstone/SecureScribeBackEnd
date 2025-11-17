from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel, field_validator

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

    @field_validator("task_items", mode="before")
    @classmethod
    def convert_task_objects(cls, v):
        """Automatically convert Task objects to dictionaries."""
        if isinstance(v, list):
            return [item.model_dump() if hasattr(item, "model_dump") else item for item in v]
        return v
