from typing import List

from app.events.base import BaseEvent, BaseListener


class EventManager:
    _listeners: List[BaseListener] = []

    @classmethod
    def register(cls, listener: BaseListener) -> None:
        cls._listeners.append(listener)
        print(f"[EventManager] Registered listener: {listener.__class__.__name__}")

    @classmethod
    def emit(cls, event: BaseEvent) -> None:
        print(f"[EventManager] Emitting event: {event.__class__.__name__}")
        for listener in cls._listeners:
            try:
                listener.handle(event)
            except Exception as e:
                print(f"[EventManager] Listener error: {listener.__class__.__name__} - {e}")

    @classmethod
    def clear(cls) -> None:
        cls._listeners.clear()
