from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional, TypedDict

from pydantic import BaseModel, Field


class MeetingState(TypedDict, total=False):
    messages: List[Dict[str, str]]
    transcript: str
    meeting_note: str
    task_items: List[Dict[str, Any]]
    is_informative: bool
    meeting_type: str
    custom_prompt: Optional[str]


class Task(BaseModel):
    description: str = Field(description="Task description in Vietnamese")
    creator_id: Optional[uuid.UUID] = Field(default=None, description="Creator user ID")
    assignee_id: Optional[uuid.UUID] = Field(default=None, description="Assignee user ID")
    status: str = Field(default="todo", description="Task status")
    priority: str = Field(default="Trung bình", description="Priority level")
    due_date: Optional[str] = Field(default=None, description="Due date")
    project_ids: List[uuid.UUID] = Field(default_factory=list, description="Related project IDs")
    notes: str = Field(default="", description="Additional notes")


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
