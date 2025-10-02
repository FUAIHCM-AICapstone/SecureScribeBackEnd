from typing import Dict, Optional, Sequence
from uuid import UUID

from sqlalchemy.orm import Session

from app.utils.meeting_summary import generate_meeting_summary


async def summarize_meeting_sections_for_chat(
    meeting_id: UUID,
    db: Session,
    user_id: UUID,
    sections: Optional[Sequence[str]] = None,
) -> Dict[str, object]:
    result = await generate_meeting_summary(db, meeting_id, user_id, sections)
    return {
        "content": result["content"],
        "summaries": result["summaries"],
        "sections": result["sections"],
    }
