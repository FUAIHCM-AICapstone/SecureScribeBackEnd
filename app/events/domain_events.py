import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional


@dataclass
class BaseDomainEvent:
    """Standardized domain event for audit logging.

    This class is intentionally minimal and serializable to dict for Celery.
    """

    event_name: str
    actor_user_id: uuid.UUID
    target_type: str
    target_id: Optional[uuid.UUID] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        # Coerce UUIDs and datetime into string/iso for JSON safety
        d["actor_user_id"] = str(self.actor_user_id) if self.actor_user_id else None
        if self.target_id is not None:
            d["target_id"] = str(self.target_id)
        d["timestamp"] = self.timestamp.isoformat()
        return d

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "BaseDomainEvent":
        return BaseDomainEvent(
            event_name=data.get("event_name"),
            actor_user_id=uuid.UUID(data["actor_user_id"]) if data.get("actor_user_id") else None,
            target_type=data.get("target_type"),
            target_id=uuid.UUID(data["target_id"]) if data.get("target_id") else None,
            metadata=data.get("metadata", {}) or {},
            timestamp=datetime.fromisoformat(data["timestamp"]) if data.get("timestamp") else datetime.now(timezone.utc),
        )


def build_diff(old: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, list[Any]]:
    """Create a compact diff mapping field -> [old, new] for changed keys only."""
    diff: Dict[str, list[Any]] = {}
    for k in new.keys():
        old_val = old.get(k)
        new_val = new.get(k)
        if old_val != new_val:
            diff[k] = [old_val, new_val]
    return diff
