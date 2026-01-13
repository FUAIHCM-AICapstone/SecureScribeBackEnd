import uuid
from typing import List, Tuple

from sqlalchemy.orm import Session

from app.crud.search import crud_search_dynamic


def search_dynamic(
    db: Session,
    search_term: str,
    user_id: uuid.UUID,
    page: int = 1,
    limit: int = 20,
    project_id: uuid.UUID = None,
    meeting_id: uuid.UUID = None,
) -> Tuple[List[dict], int]:
    return crud_search_dynamic(db, search_term, user_id, page, limit, project_id, meeting_id)
