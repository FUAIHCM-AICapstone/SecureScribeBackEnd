import json
import uuid
from typing import Iterable, List, Optional, Set

from agno.models.message import Message
from sqlalchemy.orm import Session

from app.models.chat import ChatMessage, ChatMessageType
from app.utils.llm import get_agno_postgres_db, create_chat_agent


def _normalize_mentions(raw_mentions: Optional[Iterable]) -> List[dict]:
    if not raw_mentions:
        return []
    normalized: List[dict] = []
    for mention in raw_mentions:
        if isinstance(mention, dict):
            normalized.append(mention)
        else:
            try:
                normalized.append(dict(mention))  # type: ignore[arg-type]
            except Exception:
                pass
    return normalized


def _format_mentions_summary(mentions: Optional[Iterable]) -> str:
    normalized = _normalize_mentions(mentions)
    if not normalized:
        return "No mentions supplied."

    lines = ["Mentioned context:"]
    for item in normalized:
        entity_type = item.get("entity_type", "unknown")
        entity_id = item.get("entity_id", "unknown")
        start = item.get("offset_start")
        end = item.get("offset_end")
        span = f" (offsets {start}-{end})" if start is not None and end is not None else ""
        lines.append(f"- {entity_type}: {entity_id}{span}")
    return "\n".join(lines)


def get_chat_agent(
    db: Session,
    user_id: uuid.UUID,
    session_id: str,
):
    """Factory function to create a chat agent without meeting linkage."""
    try:
        agno_db = get_agno_postgres_db()

        def mention_context_tool(mentions: str = "[]") -> str:
            try:
                payload = json.loads(mentions) if isinstance(mentions, str) else mentions
            except (ValueError, TypeError):
                payload = []
            return _format_mentions_summary(payload)

        tools: List = [mention_context_tool]

        return create_chat_agent(
            agno_db=agno_db,
            session_id=session_id,
            user_id=str(user_id),
            tools=tools,
        )
    except Exception as exc:
        print(f"Error creating chat agent: {exc}")
        return None


def _resolve_message_role(message_type: str) -> str:
    if isinstance(message_type, ChatMessageType):
        value = message_type.value
    else:
        value = str(message_type)
    if value == ChatMessageType.agent.value:
        return "assistant"
    if value == ChatMessageType.system.value:
        return "system"
    return "user"


def prime_agent_with_history(agent, history: Iterable[ChatMessage]) -> None:
    if not agent:
        return
    buffered = list(history)
    if not buffered:
        return
    seen: Set[str] = set(getattr(agent, "_secure_scribe_seen_message_ids", set()))
    fresh = [message for message in buffered if str(message.id) not in seen and message.content]
    if not fresh:
        return
    agno_messages = [
        Message(
            role=_resolve_message_role(message.message_type),
            content=message.content,
        )
        for message in fresh
    ]
    if not agno_messages:
        return
    updated = False
    memory = getattr(agent, "memory", None)
    if memory:
        if hasattr(memory, "add_messages"):
            try:
                memory.add_messages(agno_messages)
                updated = True
            except Exception:
                pass
        elif hasattr(memory, "add"):
            try:
                for msg in agno_messages:
                    memory.add(msg)
                updated = True
            except Exception:
                pass
    if not updated:
        if hasattr(agent, "add_messages"):
            try:
                agent.add_messages(agno_messages)
                updated = True
            except Exception:
                pass
        elif hasattr(agent, "add_message"):
            try:
                for msg in agno_messages:
                    agent.add_message(msg)
                updated = True
            except Exception:
                pass
    if not updated and hasattr(agent, "db") and hasattr(agent, "session_id"):
        db = getattr(agent, "db", None)
        session_id = getattr(agent, "session_id", None)
        if db and session_id:
            if hasattr(db, "add_messages"):
                try:
                    db.add_messages(session_id, agno_messages)
                    updated = True
                except Exception:
                    pass
            elif hasattr(db, "add_message"):
                try:
                    for msg in agno_messages:
                        db.add_message(session_id, msg)
                    updated = True
                except Exception:
                    pass
    if updated:
        seen.update(str(message.id) for message in fresh)
        setattr(agent, "_secure_scribe_seen_message_ids", seen)
