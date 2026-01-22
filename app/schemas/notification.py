from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class NotificationBase(BaseModel):
    type: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None
    channel: Optional[str] = None
    icon: Optional[str] = None
    badge: Optional[str] = None
    sound: Optional[str] = None
    ttl: Optional[int] = None

    class Config:
        from_attributes = True


class NotificationCreate(NotificationBase):
    user_ids: List[int]


class NotificationGlobalCreate(NotificationBase):
    pass


class NotificationResponse(NotificationBase):
    id: int
    user_id: int
    is_read: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class NotificationUpdate(BaseModel):
    is_read: Optional[bool] = None

    class Config:
        from_attributes = True


class NotificationStreamEvent(BaseModel):
    type: str
    data: Dict[str, Any]
    timestamp: datetime

    class Config:
        from_attributes = True
