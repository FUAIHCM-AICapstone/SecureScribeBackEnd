from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models.audit import AuditLog


def write_audit_log(event: Dict[str, Any], db: Optional[Session] = None) -> None:
    local_db = not db
    if local_db:
        db = SessionLocal()
    audit = AuditLog(actor_user_id=event.get("actor_user_id"), action=event.get("event_name"), target_type=event.get("target_type"), target_id=event.get("target_id"), audit_metadata=event.get("metadata"))
    db.add(audit)
    db.commit()
    if local_db:
        db.close()


class AuditLogService:
    def __init__(self, db: Optional[Session] = None) -> None:
        self._db = db

    def write_log(self, event: Dict[str, Any]) -> None:
        write_audit_log(event, db=self._db)
