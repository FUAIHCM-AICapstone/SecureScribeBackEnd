"""Audit log write utilities.

This module follows the functional style used by other service files.
Primary entrypoint: write_audit_log(event, db)
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models.audit import AuditLog


def write_audit_log(event: Dict[str, Any], db: Optional[Session] = None) -> None:
    """Persist a domain event into the audit_logs table.

    Parameters:
        event: Dict payload produced by BaseDomainEvent.to_dict()
        db: Optional existing Session (if omitted, a local session is created)
    """
    local_db = False
    if db is None:
        db = SessionLocal()
        local_db = True

    try:
        audit = AuditLog(
            actor_user_id=event.get("actor_user_id"),
            action=event.get("event_name"),
            target_type=event.get("target_type"),
            target_id=event.get("target_id"),
            audit_metadata=event.get("metadata"),
        )
        db.add(audit)
        db.commit()
    except Exception as e:  # noqa: BLE001 (intentional broad swallow per design)
        db.rollback()
        print(
            "[AuditLog] Write failed:",
            type(e).__name__,
            str(e),
            "event=",
            event.get("event_name"),
            "actor=",
            event.get("actor_user_id"),
            "target=",
            f"{event.get('target_type')}:{event.get('target_id')}",
        )
        # Swallow to avoid impacting business flow
    finally:
        if local_db:
            db.close()


class AuditLogService:
    """Thin wrapper retained for backward compatibility.

    Prefer using write_audit_log().
    """

    def __init__(self, db: Optional[Session] = None) -> None:
        self._db = db

    def write_log(self, event: Dict[str, Any]) -> None:  # pragma: no cover - simple delegation
        write_audit_log(event, db=self._db)
