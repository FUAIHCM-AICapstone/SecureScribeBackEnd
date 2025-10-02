import json
from typing import Dict, Iterable, List, Optional, Sequence
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.meeting import Meeting
from app.services.meeting import get_meeting
from app.services.transcript import get_transcript_by_meeting
from app.utils.llm import chat_complete

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


def normalize_summary_sections(sections: Optional[Sequence[str]]) -> List[str]:
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
    return normalized or list(DEFAULT_SUMMARY_SECTIONS)


def format_summary_text(sections: Iterable[str], summaries: Dict[str, str]) -> str:
    parts: List[str] = []
    for section in sections:
        content = summaries.get(section, "").strip()
        block = f"{section}:\n{content}".strip()
        if block:
            parts.append(block)
    return "\n\n".join(parts)


def parse_summary_response(sections: List[str], response: str) -> Dict[str, str]:
    parsed: Dict[str, str] = {}
    try:
        data = json.loads(response)
    except Exception:
        data = None
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, str):
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
    return parse_summary_response(sections, summary)


async def generate_meeting_summary(
    db: Session,
    meeting_id: UUID,
    user_id: UUID,
    sections: Optional[Sequence[str]] = None,
) -> Dict[str, object]:
    normalized_sections = normalize_summary_sections(sections)
    meeting = get_meeting(db, meeting_id, user_id, raise_404=True)
    transcript = get_transcript_by_meeting(db, meeting_id)
    if not transcript or not transcript.content:
        raise HTTPException(status_code=404, detail="Transcript not found")
    summaries = await _generate_section_summaries(transcript.content, normalized_sections)
    content = format_summary_text(normalized_sections, summaries)
    return {
        "meeting": meeting,
        "sections": normalized_sections,
        "summaries": summaries,
        "content": content,
    }
