import json
from datetime import datetime
from typing import Dict, Iterable, List, Optional, Sequence
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.meeting import Meeting, MeetingNote, Transcript
from app.models.user import User
from app.utils.llm import chat_complete
from app.utils.meeting import check_meeting_access

DEFAULT_SUMMARY_SECTIONS = ["Objective", "Discussion", "Decision", "Action Items"]
SECTION_ALIASES = {
    "objective": "Objective",
    "objectives": "Objective",
    "discussion": "Discussion",
    "discussions": "Discussion",
    "decision": "Decision",
    "decisions": "Decision",
    "action items": "Action Items",
    "action item": "Action Items",
    "actions": "Action Items",
    "tasks": "Action Items",
    "all": "__all__",
    "everything": "__all__",
    "full": "__all__",
}


def _normalize_sections(sections: Optional[Sequence[str]]) -> List[str]:
    if not sections:
        return list(DEFAULT_SUMMARY_SECTIONS)
    normalized: List[str] = []
    seen = set()
    for section in sections:
        key = section.strip().lower()
        if not key:
            continue
        alias = SECTION_ALIASES.get(key)
        if alias == "__all__":
            return list(DEFAULT_SUMMARY_SECTIONS)
        if not alias:
            raise HTTPException(status_code=400, detail=f"Unsupported summary section: {section}")
        if alias not in seen:
            normalized.append(alias)
            seen.add(alias)
    if not normalized:
        return list(DEFAULT_SUMMARY_SECTIONS)
    return normalized


def _format_summary_text(sections: Iterable[str], summaries: Dict[str, str]) -> str:
    parts: List[str] = []
    for section in sections:
        content = summaries.get(section, "").strip()
        parts.append(f"{section}:\n{content}".strip())
    return "\n\n".join(part for part in parts if part)


def _parse_summary_response(sections: List[str], response: str) -> Dict[str, str]:
    parsed: Dict[str, str] = {}
    try:
        data = json.loads(response)
    except Exception:
        data = None
    if isinstance(data, dict):
        for key, value in data.items():
            if not isinstance(value, str):
                continue
            for section in sections:
                if key.strip().lower() == section.lower():
                    parsed[section] = value.strip()
    if len(parsed) == len(sections):
        return parsed
    fallback: Dict[str, List[str]] = {}
    current = None
    for line in response.splitlines():
        candidate = line.strip().rstrip(":").lower()
        match = next((section for section in sections if section.lower() == candidate), None)
        if match:
            current = match
            fallback.setdefault(current, [])
            continue
        if current:
            fallback[current].append(line)
    for section in sections:
        if section in fallback:
            parsed[section] = "\n".join(fallback[section]).strip()
    if parsed:
        return parsed
    return {sections[0]: response.strip(), **{section: "" for section in sections[1:]}}


async def _generate_section_summaries(transcript_text: str, sections: List[str]) -> Dict[str, str]:
    system_prompt = "You are an assistant that summarizes meeting transcripts into structured notes."
    sections_list = ", ".join(sections)
    json_keys = ", ".join(f'"{section}"' for section in sections)
    user_prompt = (
        f"Transcript:\n{transcript_text}\n\n"
        f"Summarize the meeting for the following sections: {sections_list}. "
        f"Return a JSON object with keys [{json_keys}] where each value is a concise summary for that section. "
        f"Do not include any text outside the JSON object."
    )
    summary = await chat_complete(system_prompt, user_prompt)
    return _parse_summary_response(sections, summary)


def _should_persist(sections: List[str]) -> bool:
    return len(sections) == len(DEFAULT_SUMMARY_SECTIONS) and set(sections) == set(DEFAULT_SUMMARY_SECTIONS)


def _get_transcript(db: Session, meeting_id: UUID) -> Transcript:
    transcript = db.query(Transcript).filter(Transcript.meeting_id == meeting_id).first()
    if not transcript or not transcript.content:
        raise HTTPException(status_code=404, detail="Transcript not found")
    return transcript


def _get_meeting(db: Session, meeting_id: UUID) -> Meeting:
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id, Meeting.is_deleted == False).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return meeting


def _assert_access(db: Session, meeting: Meeting, user_id: UUID) -> None:
    if not check_meeting_access(db, meeting, user_id):
        raise HTTPException(status_code=403, detail="Access denied")


async def _build_summary(db: Session, meeting_id: UUID, user_id: UUID, sections: Optional[Sequence[str]]) -> Dict[str, object]:
    normalized_sections = _normalize_sections(sections)
    meeting = _get_meeting(db, meeting_id)
    _assert_access(db, meeting, user_id)
    transcript = _get_transcript(db, meeting_id)
    summaries = await _generate_section_summaries(transcript.content, normalized_sections)
    content = _format_summary_text(normalized_sections, summaries)
    return {
        "meeting": meeting,
        "sections": normalized_sections,
        "summaries": summaries,
        "content": content,
    }


async def summarize_meeting(meeting_id: UUID, db: Session, current_user: User, sections: Optional[Sequence[str]] = None) -> Dict[str, object]:
    result = await _build_summary(db, meeting_id, current_user.id, sections)
    summaries: Dict[str, str] = result["summaries"]  # type: ignore
    normalized_sections: List[str] = result["sections"]  # type: ignore
    content: str = result["content"]  # type: ignore
    note: Optional[MeetingNote] = None
    if _should_persist(normalized_sections):
        now = datetime.utcnow()
        note = db.query(MeetingNote).filter(MeetingNote.meeting_id == meeting_id).first()
        if note:
            note.content = content
            note.last_editor_id = current_user.id
            note.last_edited_at = now
        else:
            note = MeetingNote(meeting_id=meeting_id, content=content, last_editor_id=current_user.id, last_edited_at=now)
            db.add(note)
        db.commit()
        db.refresh(note)
    return {
        "note": note,
        "content": content,
        "summaries": summaries,
        "sections": normalized_sections,
    }


async def summarize_meeting_sections_for_chat(meeting_id: UUID, db: Session, user_id: UUID, sections: Optional[Sequence[str]] = None) -> Dict[str, object]:
    result = await _build_summary(db, meeting_id, user_id, sections)
    return {
        "content": result["content"],
        "summaries": result["summaries"],
        "sections": result["sections"],
    }
