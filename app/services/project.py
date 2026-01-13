import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.crud.project import crud_add_user_to_project, crud_create_project, crud_delete_project_with_cascade, crud_get_project, crud_get_project_members, crud_get_projects, crud_get_user_role_in_project, crud_is_user_in_project, crud_remove_user_from_project, crud_update_project, crud_update_user_role_in_project
from app.events.domain_events import BaseDomainEvent
from app.events.project_events import UserAddedToProjectEvent, UserRemovedFromProjectEvent
from app.models.project import Project, UserProject
from app.schemas.project import ProjectCreate, ProjectFilter, ProjectUpdate, UserProjectCreate
from app.services.event_manager import EventManager


def create_project(db: Session, project_data: ProjectCreate, created_by: uuid.UUID) -> Project:
    project = crud_create_project(db, project_data.name, project_data.description, created_by)
    EventManager.emit_domain_event(BaseDomainEvent(event_name="project.created", actor_user_id=created_by, target_type="project", target_id=project.id, metadata={"name": project.name}))
    crud_add_user_to_project(db, project.id, created_by, "owner")
    return project


def get_project(db: Session, project_id: uuid.UUID, include_members: bool = False) -> Optional[Project]:
    return crud_get_project(db, project_id, include_members)


def get_projects(db: Session, filters: Optional[ProjectFilter] = None, page: int = 1, limit: int = 20, order_by: str = "created_at", dir: str = "desc") -> tuple[List[Project], int]:
    return crud_get_projects(db, filters.model_dump() if filters else None, page=page, limit=limit, order_by=order_by, dir=dir)


def update_project(db: Session, project_id: uuid.UUID, updates: ProjectUpdate, actor_user_id: uuid.UUID | None = None) -> Optional[Project]:
    project = crud_update_project(db, project_id, **updates.model_dump(exclude_unset=True))
    if project and actor_user_id:
        EventManager.emit_domain_event(BaseDomainEvent(event_name="project.updated", actor_user_id=actor_user_id, target_type="project", target_id=project.id, metadata={"updates": updates.model_dump(exclude_unset=True)}))
    return project


def delete_project(db: Session, project_id: uuid.UUID, actor_user_id: uuid.UUID | None = None) -> bool:
    result = crud_delete_project_with_cascade(db, project_id)
    if result and actor_user_id:
        EventManager.emit_domain_event(BaseDomainEvent(event_name="project.deleted", actor_user_id=actor_user_id, target_type="project", target_id=project_id, metadata={}))
    return result


# User-Project relationship management
def add_user_to_project(db: Session, project_id: uuid.UUID, user_id: uuid.UUID, role: str = "member", added_by_user_id: uuid.UUID = None) -> Optional[UserProject]:
    user_project = crud_add_user_to_project(db, project_id, user_id, role)
    if user_project and added_by_user_id:
        event = UserAddedToProjectEvent(project_id=project_id, user_id=user_id, added_by_user_id=added_by_user_id, db=db)
        EventManager.emit(event)
        EventManager.emit_domain_event(BaseDomainEvent(event_name="project.member_added", actor_user_id=added_by_user_id, target_type="project", target_id=project_id, metadata={"added_user_id": str(user_id), "role": role}))
    return user_project


def remove_user_from_project(db: Session, project_id: uuid.UUID, user_id: uuid.UUID, removed_by_user_id: uuid.UUID = None, is_self_removal: bool = False) -> bool:
    result = crud_remove_user_from_project(db, project_id, user_id)
    if result and removed_by_user_id:
        event = UserRemovedFromProjectEvent(project_id=project_id, user_id=user_id, removed_by_user_id=removed_by_user_id, db=db, is_self_removal=is_self_removal)
        EventManager.emit(event)
        EventManager.emit_domain_event(BaseDomainEvent(event_name="project.member_removed", actor_user_id=removed_by_user_id, target_type="project", target_id=project_id, metadata={"removed_user_id": str(user_id), "is_self_removal": is_self_removal}))
    return result


def update_user_role_in_project(db: Session, project_id: uuid.UUID, user_id: uuid.UUID, new_role: str, actor_user_id: uuid.UUID | None = None) -> Optional[UserProject]:
    user_project = crud_update_user_role_in_project(db, project_id, user_id, new_role)
    if user_project and actor_user_id:
        EventManager.emit_domain_event(BaseDomainEvent(event_name="project.member_role_updated", actor_user_id=actor_user_id, target_type="project", target_id=project_id, metadata={"user_id": str(user_id), "new_role": new_role}))
    return user_project


def get_project_members(db: Session, project_id: uuid.UUID) -> List[UserProject]:
    return crud_get_project_members(db, project_id)


def is_user_in_project(db: Session, project_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    return crud_is_user_in_project(db, project_id, user_id)


def get_user_role_in_project(db: Session, project_id: uuid.UUID, user_id: uuid.UUID) -> Optional[str]:
    return crud_get_user_role_in_project(db, project_id, user_id)


# Bulk operations
def bulk_add_users_to_project(db: Session, project_id: uuid.UUID, users_data: List[UserProjectCreate], added_by_user_id: uuid.UUID = None) -> List[Dict[str, Any]]:
    results = []
    for user_data in users_data:
        user_project = add_user_to_project(db, project_id, user_data.user_id, user_data.role, added_by_user_id)
        results.append({"success": user_project is not None, "user_id": str(user_data.user_id)})
    return results


def bulk_remove_users_from_project(db: Session, project_id: uuid.UUID, user_ids: List[uuid.UUID]) -> List[Dict[str, Any]]:
    results = []
    for user_id in user_ids:
        success = remove_user_from_project(db, project_id, user_id)
        results.append({"success": success, "user_id": str(user_id)})
    return results
