import uuid
from typing import List, Optional, Tuple

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.tag import MeetingTag, Tag
from app.schemas.tag import TagCreate, TagFilter, TagUpdate
from app.utils.tag import check_tag_access_permission, check_tag_create_permission


def create_tag(db: Session, tag_data: TagCreate, created_by: uuid.UUID) -> Tag:
    if not check_tag_create_permission(db, created_by):
        raise HTTPException(status_code=403, detail="No permission to create tags")
    tag = Tag(name=tag_data.name, scope=tag_data.scope, created_by=created_by)
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag


def get_tag(db: Session, tag_id: uuid.UUID, user_id: uuid.UUID) -> Optional[Tag]:
    tag = db.query(Tag).filter(Tag.id == tag_id, Tag.is_deleted == False).first()
    if not tag:
        return None
    accessible_projects = check_tag_access_permission(db, user_id)
    if not accessible_projects:
        return None
    return tag


def get_tags(db: Session, filters: TagFilter, user_id: uuid.UUID, page: int = 1, limit: int = 10) -> Tuple[List[Tag], int]:
    query = db.query(Tag).filter(Tag.is_deleted == False)
    accessible_projects = check_tag_access_permission(db, user_id)
    if not accessible_projects:
        return [], 0
    if filters.name:
        query = query.filter(Tag.name.ilike(f"%{filters.name}%"))
    if filters.scope:
        query = query.filter(Tag.scope == filters.scope)
    if filters.created_by:
        query = query.filter(Tag.created_by == filters.created_by)
    total = query.count()
    tags = query.offset((page - 1) * limit).limit(limit).all()
    return tags, total


def update_tag(db: Session, tag_id: uuid.UUID, update_data: TagUpdate, user_id: uuid.UUID) -> Tag:
    tag = get_tag(db, tag_id, user_id)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    for field, value in update_data.dict(exclude_unset=True).items():
        setattr(tag, field, value)
    db.commit()
    db.refresh(tag)
    return tag


def delete_tag(db: Session, tag_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    tag = get_tag(db, tag_id, user_id)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    tag.is_deleted = True
    db.commit()
    return True


def bulk_create_tags(db: Session, tags_data: List[TagCreate], created_by: uuid.UUID) -> List[Tag]:
    if not check_tag_create_permission(db, created_by):
        raise HTTPException(status_code=403, detail="No permission to create tags")
    tags = [Tag(name=tag_data.name, scope=tag_data.scope, created_by=created_by) for tag_data in tags_data]
    db.add_all(tags)
    db.commit()
    for tag in tags:
        db.refresh(tag)
    return tags


def bulk_update_tags(db: Session, updates_data: List[dict], user_id: uuid.UUID) -> List[Tag]:
    updated_tags = []
    for update_data in updates_data:
        tag_id = update_data.pop("id")
        tag = update_tag(db, tag_id, TagUpdate(**update_data), user_id)
        updated_tags.append(tag)
    return updated_tags


def bulk_delete_tags(db: Session, tag_ids: List[uuid.UUID], user_id: uuid.UUID) -> bool:
    for tag_id in tag_ids:
        delete_tag(db, tag_id, user_id)
    return True


def search_tags(db: Session, query: str, filters: TagFilter, user_id: uuid.UUID) -> List[Tag]:
    accessible_projects = check_tag_access_permission(db, user_id)
    if not accessible_projects:
        return []
    q = db.query(Tag).filter(Tag.is_deleted == False, Tag.name.ilike(f"%{query}%"))
    if filters.scope:
        q = q.filter(Tag.scope == filters.scope)
    if filters.created_by:
        q = q.filter(Tag.created_by == filters.created_by)
    return q.all()


def get_user_tags(db: Session, user_id: uuid.UUID) -> List[Tag]:
    return db.query(Tag).filter(Tag.created_by == user_id, Tag.is_deleted == False).all()


def get_tag_statistics(db: Session, tag_ids: Optional[List[uuid.UUID]] = None) -> dict:
    query = db.query(Tag.id, func.count(MeetingTag.meeting_id).label("meeting_count")).join(MeetingTag, Tag.id == MeetingTag.tag_id).filter(Tag.is_deleted == False).group_by(Tag.id)
    if tag_ids:
        query = query.filter(Tag.id.in_(tag_ids))
    return {str(row.id): row.meeting_count for row in query.all()}
