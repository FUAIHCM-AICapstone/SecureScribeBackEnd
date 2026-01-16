from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, field_validator


class MeetingAgendaRequest(BaseModel):
    content: str

    @field_validator("content")
    @classmethod
    def validate_content_length(cls, v):
        if len(v) > 50000:
            raise ValueError("Content must not exceed 50000 characters")
        return v


class MeetingAgendaResponse(BaseModel):
    id: str
    content: Optional[str] = None
    last_edited_at: Optional[str] = None
    created_at: str
    updated_at: Optional[str] = None


class TokenUsage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class MeetingAgendaGenerateResponse(BaseModel):
    agenda: MeetingAgendaResponse
    content: str
    token_usage: Optional[Dict[str, Any]] = None
