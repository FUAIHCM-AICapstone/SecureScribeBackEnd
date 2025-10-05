import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import get_db
from app.models.user import User
from app.schemas.common import PaginatedResponse, create_pagination_meta
from app.schemas.tag import TagApiResponse, TagFilter, TagsPaginatedResponse, TagStatsResponse, TagUpdate
from app.services.tag import (
    bulk_create_tags,
    bulk_delete_tags,
    bulk_update_tags,
    create_tag,
    delete_tag,
    get_tag,
    get_tag_statistics,
    get_tags,
    get_user_tags,
    search_tags,
    update_tag,
)
from app.utils.auth import get_current_user

router = APIRouter(prefix=settings.API_V1_STR, tags=["Tag"])


@router.post("/tags", response_model=TagApiResponse)
def create_tag_endpoint(tag: dict, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    new_tag = create_tag(db, tag, current_user.id)
    return {"success": True, "message": "Tag created successfully", "data": new_tag}


@router.get("/tags", response_model=TagsPaginatedResponse)
def get_tags_endpoint(
    name: Optional[str] = None,
    scope: Optional[str] = None,
    created_by: Optional[uuid.UUID] = None,
    project_id: Optional[uuid.UUID] = None,
    min_usage_count: Optional[int] = None,
    max_usage_count: Optional[int] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    filters = TagFilter(
        name=name,
        scope=scope,
        created_by=created_by,
        project_id=project_id,
        min_usage_count=min_usage_count,
        max_usage_count=max_usage_count,
    )
    tags, total = get_tags(db, filters, current_user.id, page, limit)
    pagination_meta = create_pagination_meta(page, limit, total)
    return PaginatedResponse(
        success=True,
        message="Tags retrieved successfully",
        data=tags,
        pagination=pagination_meta,
    )


@router.get("/tags/{tag_id}", response_model=TagApiResponse)
def get_tag_endpoint(tag_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    tag = get_tag(db, tag_id, current_user.id)
    if not tag:
        return {"success": False, "message": "Tag not found", "data": None}
    stats = get_tag_statistics(db, [tag_id])
    tag.meeting_count = stats.get(str(tag_id), 0)
    return {"success": True, "message": "Tag retrieved successfully", "data": tag}


@router.put("/tags/{tag_id}", response_model=TagApiResponse)
def update_tag_endpoint(tag_id: uuid.UUID, tag_update: TagUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    updated_tag = update_tag(db, tag_id, tag_update, current_user.id)
    return {"success": True, "message": "Tag updated successfully", "data": updated_tag}


@router.delete("/tags/{tag_id}", response_model=dict)
def delete_tag_endpoint(tag_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    delete_tag(db, tag_id, current_user.id)
    return {"success": True, "message": "Tag deleted successfully"}


@router.post("/tags/bulk", response_model=dict)
def bulk_tags_endpoint(
    action: str,
    bulk_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if action == "create":
        tags = bulk_create_tags(db, bulk_data["tags"], current_user.id)
        return {"success": True, "message": f"{len(tags)} tags created successfully", "data": tags}
    elif action == "update":
        tags = bulk_update_tags(db, bulk_data["updates"], current_user.id)
        return {"success": True, "message": f"{len(tags)} tags updated successfully", "data": tags}
    elif action == "delete":
        bulk_delete_tags(db, bulk_data["tag_ids"], current_user.id)
        return {"success": True, "message": f"{len(bulk_data['tag_ids'])} tags deleted successfully"}
    return {"success": False, "message": "Invalid action"}


@router.get("/tags/search", response_model=dict)
def search_tags_endpoint(
    q: str,
    scope: Optional[str] = None,
    created_by: Optional[uuid.UUID] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    filters = TagFilter(scope=scope, created_by=created_by)
    tags = search_tags(db, q, filters, current_user.id)
    return {"success": True, "message": "Tags searched successfully", "data": tags}


@router.get("/tags/statistics", response_model=TagStatsResponse)
def get_tag_statistics_endpoint(tag_ids: Optional[str] = None, db: Session = Depends(get_db)):
    tag_id_list = [uuid.UUID(tid.strip()) for tid in tag_ids.split(",")] if tag_ids else None
    stats = get_tag_statistics(db, tag_id_list)
    return {"success": True, "message": "Tag statistics retrieved successfully", "data": stats}


@router.get("/users/me/tags", response_model=dict)
def get_user_tags_endpoint(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    tags = get_user_tags(db, current_user.id)
    return {"success": True, "message": "User tags retrieved successfully", "data": tags}
