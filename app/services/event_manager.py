from typing import Any, Dict, List

from app.events.base import BaseEvent, BaseListener
from app.events.domain_events import BaseDomainEvent
from app.jobs.tasks import process_domain_event
from app.utils.logging import logger


class EventManager:
    _listeners: List[BaseListener] = []

    @classmethod
    def register(cls, listener: BaseListener) -> None:
        cls._listeners.append(listener)
        logger.info(f"[EventManager] Registered listener: {listener.__class__.__name__}")

    @classmethod
    def emit(cls, event: BaseEvent) -> None:
        logger.debug(f"[EventManager] Emitting event: {event.__class__.__name__}")
        for listener in cls._listeners:
            try:
                listener.handle(event)
            except Exception as e:
                logger.error(f"[EventManager] Listener error: {listener.__class__.__name__} - {e}", exc_info=True)

    @classmethod
    def emit_domain_event(cls, event: BaseDomainEvent | Dict[str, Any]) -> None:
        """Enqueue a domain event to Celery for audit logging.

        This must remain lightweight and MUST NOT perform business logic.
        """
        try:
            payload = event.to_dict() if isinstance(event, BaseDomainEvent) else event
            process_domain_event.delay(payload)
            logger.debug(f"[EventManager] Enqueued domain event: {payload.get('event_name')}")
        except Exception as e:
            # Do not raise to callers; audit must not affect business flow
            logger.warning(f"[EventManager] Failed to enqueue domain event: {e}")

    @classmethod
    def clear(cls) -> None:
        cls._listeners.clear()
