from __future__ import annotations

from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models.audit import AuditLog


class AuditLogService:
    """Single-responsibility service to write audit logs.

    This service does not perform business validation. It simply persists
    the provided event payload into the audit_logs table.
    """

    def __init__(self, db: Optional[Session] = None) -> None:
        self._external_db = db

    def write_log(self, event: Dict[str, Any]) -> None:
        db = self._external_db or SessionLocal()

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
        except Exception:
            db.rollback()
            # Intentionally swallow exceptions to keep worker lightweight.
            # In a more advanced setup, we would report to Sentry here.
            raise
        finally:
            if self._external_db is None:
                db.close()
