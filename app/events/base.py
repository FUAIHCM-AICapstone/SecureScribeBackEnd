from abc import ABC, abstractmethod
from datetime import datetime


class BaseEvent(ABC):
    def __init__(self, timestamp: datetime = None):
        self.timestamp = timestamp or datetime.utcnow()


class BaseListener(ABC):
    @abstractmethod
    def handle(self, event: BaseEvent) -> None:
        pass
