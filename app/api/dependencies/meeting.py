import uuid
from typing import Optional

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.meeting import Meeting
from app.models.user import User
from app.services.meeting import get_meeting
from app.utils.auth import get_current_user
from app.utils.meeting import can_delete_meeting


def get_meeting_or_404(
    meeting_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Meeting:
    """Get meeting or raise 404"""
    meeting = get_meeting(db, meeting_id, current_user.id)
    if not meeting:
        raise HTTPException(
            status_code=404, detail="Meeting not found or access denied"
        )
    return meeting


def check_delete_permissions(
    meeting: Meeting = Depends(get_meeting_or_404),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Meeting:
    """Check if user can delete meeting"""
    if not can_delete_meeting(db, meeting, current_user.id):
        raise HTTPException(
            status_code=403, detail="You don't have permission to delete this meeting"
        )
    return meeting
