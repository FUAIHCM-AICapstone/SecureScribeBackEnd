import uuid
from typing import List

from sqlalchemy.orm import Session

from app.models.project import UserProject


def check_tag_create_permission(db: Session, user_id: uuid.UUID) -> bool:
    return db.query(UserProject).filter(UserProject.user_id == user_id).first() is not None


def check_tag_access_permission(db: Session, user_id: uuid.UUID) -> List[uuid.UUID]:
    return [up.project_id for up in db.query(UserProject).filter(UserProject.user_id == user_id).all()]


def get_user_accessible_projects(db: Session, user_id: uuid.UUID) -> List[uuid.UUID]:
    return [up.project_id for up in db.query(UserProject).filter(UserProject.user_id == user_id).all()]
