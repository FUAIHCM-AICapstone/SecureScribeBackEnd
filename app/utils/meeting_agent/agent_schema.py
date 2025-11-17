from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, TypedDict

from pydantic import BaseModel, Field

from app.utils.meeting_agent.date_parser import parse_due_date_to_datetime


class MeetingState(TypedDict, total=False):
    messages: List[Dict[str, str]]
    transcript: str
    meeting_note: str
    task_items: List[Dict[str, Any]]
    is_informative: bool
    meeting_type: str
    custom_prompt: Optional[str]


class Task(BaseModel):
    title: str = Field(description="Task title in Vietnamese")
    description: str = Field(description="Task description in Vietnamese")
    creator_id: Optional[uuid.UUID] = Field(default=None, description="Creator user ID")
    assignee_id: Optional[uuid.UUID] = Field(default=None, description="Assignee user ID")
    status: str = Field(default="todo", description="Task status")
    priority: str = Field(default="Trung bình", description="Priority level")
    due_date: Optional[datetime] = Field(default=None, description="Due date (parsed from string)")
    project_ids: List[uuid.UUID] = Field(default_factory=list, description="Related project IDs")
    notes: str = Field(default="", description="Additional notes")

    def __init__(self, **data):
        """Initialize Task and parse due_date if it's a string."""
        # If due_date is provided as a string, parse it to datetime
        if "due_date" in data and isinstance(data["due_date"], str):
            data["due_date"] = parse_due_date_to_datetime(data["due_date"])
        super().__init__(**data)


class MeetingTypeResult(BaseModel):
    meeting_type: str = Field(description="Detected meeting type")
    reasoning: Optional[str] = Field(default=None, description="Explanation for the detection")


class InformativeCheckResult(BaseModel):
    is_informative: bool = Field(description="Whether the transcript has enough content")
    reason: Optional[str] = Field(default=None, description="Explanation for the decision")


class TaskItems(BaseModel):
    tasks: List[Task] = Field(default_factory=list, description="Task collection wrapper")


class MeetingNoteResult(BaseModel):
    meeting_note: str = Field(description="Markdown formatted meeting note")


class MeetingOutput(BaseModel):
    meeting_note: str = Field(description="Markdown formatted meeting note")
    task_items: List[Task] = Field(default_factory=list, description="Extracted tasks")
    is_informative: bool = Field(description="Whether the transcript has enough content")
    meeting_type: str = Field(description="Detected meeting type")
