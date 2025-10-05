from uuid import uuid4

from app.models.chat import ChatMessageType
from app.schemas.chat import ChatSessionCreate
from app.services.chat import (
    create_chat_message,
    create_chat_session,
    get_chat_history,
    get_chat_sessions_for_user,
)


def test_create_chat_session_without_meeting(db, test_user):
    session = create_chat_session(db, test_user.id, ChatSessionCreate(title="Notes"))

    assert session.user_id == test_user.id
    assert session.title == "Notes"
    assert hasattr(session, "agno_session_id")
    assert not hasattr(session, "meeting_id")

    sessions, total = get_chat_sessions_for_user(db, test_user.id)
    assert total >= 1
    assert any(item.id == session.id for item in sessions)


def test_chat_message_mentions_persist(db, test_user):
    session = create_chat_session(db, test_user.id, ChatSessionCreate(title="Mentions"))

    mentions = [
        {
            "entity_type": "project",
            "entity_id": str(uuid4()),
            "offset_start": 6,
            "offset_end": 20,
        }
    ]

    message = create_chat_message(
        db,
        session.id,
        test_user.id,
        "Working on @project",
        ChatMessageType.user,
        mentions=mentions,
    )

    assert message is not None
    assert message.mentions == mentions

    history = get_chat_history(db, session.id, test_user.id, limit=5)
    assert history
    assert history[0].mentions == mentions
