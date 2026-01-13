import uuid
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session, joinedload

from app.models.file import File
from app.models.meeting import ProjectMeeting
from app.models.project import Project, UserProject


def crud_create_project(db: Session, name: str, description: str, created_by: uuid.UUID) -> Project:
    project = Project(
        name=name,
        description=description,
        created_by=created_by,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def crud_get_project(db: Session, project_id: uuid.UUID, include_members: bool = False) -> Optional[Project]:
    if include_members:
        return (
            db.query(Project)
            .options(
                joinedload(Project.members).joinedload(UserProject.user),
                joinedload(Project.created_by_user),
            )
            .filter(Project.id == project_id)
            .first()
        )
    return db.query(Project).filter(Project.id == project_id).first()


def crud_get_projects(db: Session, filters: Dict[str, Any] = None, **kwargs) -> Tuple[List[Project], int]:
    query = db.query(Project).options(
        joinedload(Project.created_by_user),
        joinedload(Project.members).joinedload(UserProject.user),
    )

    if filters:
        if "name" in filters and filters["name"]:
            query = query.filter(Project.name.ilike(f"%{filters['name']}%"))
        if "created_by" in filters and filters["created_by"]:
            query = query.filter(Project.created_by == filters["created_by"])
        if "is_archived" in filters and filters["is_archived"] is not None:
            query = query.filter(Project.is_archived == filters["is_archived"])
        if "created_at_gte" in filters and filters["created_at_gte"]:
            query = query.filter(Project.created_at >= filters["created_at_gte"])
        if "created_at_lte" in filters and filters["created_at_lte"]:
            query = query.filter(Project.created_at <= filters["created_at_lte"])
        if "member_id" in filters and filters["member_id"]:
            query = query.join(UserProject).filter(UserProject.user_id == filters["member_id"])
        if "user_id" in filters and filters["user_id"]:
            query = query.join(UserProject).filter(UserProject.user_id == filters["user_id"])

    total = query.count()
    order_by = kwargs.get("order_by", "created_at")
    dir = kwargs.get("dir", "desc")
    if hasattr(Project, order_by):
        order_column = getattr(Project, order_by)
        if dir.lower() == "desc":
            query = query.order_by(order_column.desc())
        else:
            query = query.order_by(order_column.asc())

    page = int(kwargs.get("page", 1))
    limit = int(kwargs.get("limit", 20))
    offset = (page - 1) * limit
    query = query.offset(offset).limit(limit)

    projects = query.all()
    return projects, total


def crud_update_project(db: Session, project_id: uuid.UUID, **updates) -> Optional[Project]:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        return None
    for key, value in updates.items():
        if hasattr(project, key):
            setattr(project, key, value)
    db.commit()
    db.refresh(project)
    return project


def crud_delete_project_with_cascade(db: Session, project_id: uuid.UUID) -> bool:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        return False

    # Delete UserProject relationships
    db.query(UserProject).filter(UserProject.project_id == project_id).delete()

    # Delete ProjectMeeting relationships
    db.query(ProjectMeeting).filter(ProjectMeeting.project_id == project_id).delete()

    # Update Files - set project_id to NULL
    db.query(File).filter(File.project_id == project_id).update({"project_id": None})

    # Finally delete the project
    db.delete(project)
    db.commit()
    return True


def crud_add_user_to_project(db: Session, project_id: uuid.UUID, user_id: uuid.UUID, role: str = "member") -> Optional[UserProject]:
    user_project = UserProject(
        project_id=project_id,
        user_id=user_id,
        role=role,
    )
    db.add(user_project)
    db.commit()
    db.refresh(user_project)
    return user_project


def crud_remove_user_from_project(db: Session, project_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    user_project = db.query(UserProject).filter(UserProject.project_id == project_id, UserProject.user_id == user_id).first()
    if not user_project:
        return False
    db.delete(user_project)
    db.commit()
    return True


def crud_update_user_role_in_project(db: Session, project_id: uuid.UUID, user_id: uuid.UUID, role: str) -> Optional[UserProject]:
    user_project = db.query(UserProject).filter(UserProject.project_id == project_id, UserProject.user_id == user_id).first()
    if not user_project:
        return None
    user_project.role = role
    db.commit()
    db.refresh(user_project)
    return user_project


def crud_get_project_members(db: Session, project_id: uuid.UUID) -> List[UserProject]:
    return db.query(UserProject).options(joinedload(UserProject.user)).filter(UserProject.project_id == project_id).all()


def crud_is_user_in_project(db: Session, project_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    user_project = db.query(UserProject).filter(UserProject.project_id == project_id, UserProject.user_id == user_id).first()
    return user_project is not None


def crud_get_user_role_in_project(db: Session, project_id: uuid.UUID, user_id: uuid.UUID) -> Optional[str]:
    user_project = db.query(UserProject).filter(UserProject.project_id == project_id, UserProject.user_id == user_id).first()
    return user_project.role if user_project else None
