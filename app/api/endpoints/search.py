import uuid
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.constants.messages import MessageConstants
from app.core.config import settings
from app.db import get_db
from app.models.user import User
from app.schemas.common import ApiResponse, create_pagination_meta
from app.services.search import search_dynamic
from app.utils.auth import get_current_user

router = APIRouter(prefix=settings.API_V1_STR, tags=["Search"])


@router.get("/search/dynamic", response_model=ApiResponse)
def dynamic_search(
    search: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    page: int = 1,
    limit: int = 20,
    project_id: Optional[uuid.UUID] = None,
    meeting_id: Optional[uuid.UUID] = None,
):
    """Dynamic search across meetings, projects, and files by title/name/filename."""
    results, total = search_dynamic(db, search, current_user.id, page, limit, project_id, meeting_id)
    pagination_meta = create_pagination_meta(page, limit, total)
    return ApiResponse(
        success=True,
        message=MessageConstants.SEARCH_COMPLETED_SUCCESS if results else MessageConstants.SEARCH_NO_RESULTS,
        data=results,
        pagination=pagination_meta,
    )
