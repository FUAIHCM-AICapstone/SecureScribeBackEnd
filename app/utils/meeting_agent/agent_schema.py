from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict

from pydantic import BaseModel, Field


def _normalize_topics(values: Optional[List[Any]]) -> List[str]:
    """Normalize topic strings to lowercase snake_case."""
    if not values:
        return []

    normalized: List[str] = []
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if not text:
            continue
        text = text.replace(" ", "_").replace("-", "_")
        text = "".join(ch for ch in text if ch.isalnum() or ch == "_")
        candidate = text.strip("_").lower()
        if candidate:
            normalized.append(candidate)
    return normalized


class MeetingState(TypedDict, total=False):
    messages: List[Dict[str, str]]
    transcript: str
    meeting_note: str
    task_items: List[Dict[str, Any]]
    decision_items: List[Dict[str, Any]]
    question_items: List[Dict[str, Any]]
    token_usage: Dict[str, Any]
    is_informative: bool
    meeting_type: str
    custom_prompt: Optional[str]


class Task(BaseModel):
    description: str = Field(description="Task description in Vietnamese")
    assignee: str = Field(default="Chưa xác định", description="Assignee name if known")
    deadline: Optional[str] = Field(default="Cần xác định sau", description="Due date or note")
    priority: str = Field(default="Trung bình", description="Priority level")
    status: str = Field(default="Chưa bắt đầu", description="Progress status")
    related_topic: List[str] = Field(default_factory=list, description="Normalized related topics")
    notes: str = Field(default="Không có ghi chú", description="Additional notes if any")

    def __init__(self, **data: Any):
        related_topic = data.get("related_topic")
        data["related_topic"] = _normalize_topics(related_topic)
        if not data.get("assignee"):
            data["assignee"] = "Chưa xác định"
        if data.get("deadline") is None:
            data["deadline"] = "Cần xác định sau"
        if not data.get("priority"):
            data["priority"] = "Trung bình"
        if not data.get("status"):
            data["status"] = "Chưa bắt đầu"
        if not data.get("notes"):
            data["notes"] = "Không có ghi chú"
        super().__init__(**data)


class Decision(BaseModel):
    topic: List[str] = Field(default_factory=list, description="Normalized decision topics")
    decision: str = Field(description="Decision content in Vietnamese")
    impact: Optional[str] = Field(default=None, description="Impact of the decision")
    timeline: Optional[str] = Field(default=None, description="Implementation timeline")
    stakeholders: List[str] = Field(default_factory=list, description="Stakeholders involved")
    next_steps: Optional[List[str]] = Field(default=None, description="Follow-up actions if mentioned")

    def __init__(self, **data: Any):
        data["topic"] = _normalize_topics(data.get("topic"))
        super().__init__(**data)


class Question(BaseModel):
    question: str = Field(description="Question content in Vietnamese")
    asker: Optional[str] = Field(default=None, description="Person asking the question")
    answer: Optional[str] = Field(default=None, description="Answer provided if any")
    answered: bool = Field(description="Whether the question was answered")
    topic: List[str] = Field(default_factory=list, description="Normalized related topics")
    follow_up_actions: List[Task] = Field(default_factory=list, description="Follow-up tasks if requested")
    context: Optional[str] = Field(default=None, description="Additional context for the question")
    importance: Optional[str] = Field(default=None, description="Importance level if noted")

    def __init__(self, **data: Any):
        data["topic"] = _normalize_topics(data.get("topic"))
        super().__init__(**data)


class TaskItems(BaseModel):
    tasks: List[Task] = Field(default_factory=list, description="Task collection wrapper")


class DecisionItems(BaseModel):
    decisions: List[Decision] = Field(default_factory=list, description="Decision collection wrapper")


class QuestionItems(BaseModel):
    questions: List[Question] = Field(default_factory=list, description="Question collection wrapper")


class MeetingTypeResult(BaseModel):
    meeting_type: str = Field(description="Detected meeting type")
    reasoning: Optional[str] = Field(default=None, description="Explanation for the detection")


class InformativeCheckResult(BaseModel):
    is_informative: bool = Field(description="Whether the transcript has enough content")
    reason: Optional[str] = Field(default=None, description="Explanation for the decision")


class SummaryExtractionResult(BaseModel):
    tasks: List[Task] = Field(default_factory=list, description="Extracted tasks")
    decisions: List[Decision] = Field(default_factory=list, description="Extracted decisions")
    questions: List[Question] = Field(default_factory=list, description="Extracted questions")


class MeetingNoteResult(BaseModel):
    meeting_note: str = Field(description="Markdown formatted meeting note")


class TokenUsage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    context_tokens: int = 0
    total_tokens: int = 0
    price_usd: float = 0.0


class MeetingOutput(BaseModel):
    meeting_note: str
    task_items: List[Task]
    decision_items: List[Decision]
    question_items: List[Question]
    token_usage: Dict[str, Any]
    is_informative: bool
    meeting_type: str
