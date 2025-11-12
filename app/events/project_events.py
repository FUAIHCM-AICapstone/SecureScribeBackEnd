import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.events.base import BaseEvent


class UserAddedToProjectEvent(BaseEvent):
    def __init__(
        self,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        added_by_user_id: uuid.UUID,
        db: Session,
        timestamp: datetime = None,
    ):
        super().__init__(timestamp)
        self.project_id = project_id
        self.user_id = user_id
        self.added_by_user_id = added_by_user_id
        self.db = db


class UserRemovedFromProjectEvent(BaseEvent):
    def __init__(
        self,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        removed_by_user_id: uuid.UUID,
        db: Session,
        is_self_removal: bool = False,
        timestamp: datetime = None,
    ):
        super().__init__(timestamp)
        self.project_id = project_id
        self.user_id = user_id
        self.removed_by_user_id = removed_by_user_id
        self.db = db
        self.is_self_removal = is_self_removal
