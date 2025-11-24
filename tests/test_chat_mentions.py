import json
import types

import pytest
from qdrant_client import models as qmodels

from app.schemas.chat import Mention
from app.services import chat as chat_service
from app.services import qdrant_service


@pytest.mark.asyncio
async def test_query_documents_for_mentions_routes_by_entity(monkeypatch):
    mentions = [
        Mention(entity_type="meeting", entity_id="meeting-123", offset_start=0, offset_end=10),
        Mention(entity_type="project", entity_id="project-456", offset_start=11, offset_end=21),
        Mention(entity_type="file", entity_id="file-789", offset_start=22, offset_end=32),
        Mention(entity_type="unknown", entity_id="ignored", offset_start=33, offset_end=40),
    ]

    calls = []

    async def fake_meeting_query(entity_id: str, top_k: int = 5):
        calls.append(("meeting", entity_id, top_k))
        return [{"payload": {"text": "meeting doc"}}]

    async def fake_project_query(entity_id: str, top_k: int = 5):
        calls.append(("project", entity_id, top_k))
        return [{"payload": {"text": "project doc"}}]

    async def fake_file_query(entity_id: str, top_k: int = 5):
        calls.append(("file", entity_id, top_k))
        return [{"payload": {"text": "file doc"}}]

    monkeypatch.setattr(chat_service, "query_documents_by_meeting_id", fake_meeting_query)
    monkeypatch.setattr(chat_service, "query_documents_by_project_id", fake_project_query)
    monkeypatch.setattr(chat_service, "query_documents_by_file_id", fake_file_query)

    results = await chat_service.query_documents_for_mentions(mentions)

    assert len(results) == 3
    assert ("meeting", "meeting-123", 5) in calls
    assert ("project", "project-456", 5) in calls
    assert ("file", "file-789", 5) in calls
    assert all(call[1] != "ignored" for call in calls)


@pytest.mark.asyncio
async def test_query_documents_for_mentions_merges_expansion(monkeypatch):
    mentions = [Mention(entity_type="meeting", entity_id="meeting-123", offset_start=0, offset_end=10)]

    async def fake_meeting_query(entity_id: str, top_k: int = 5, **_kwargs):
        return [
            {
                "id": "mention-doc",
                "score": 0.4,
                "payload": {"file_id": "file-a", "chunk_index": 0, "text": "meeting note"},
                "key": "file-a:0",
            }
        ]

    class ExpansionCapture:
        def __init__(self):
            self.called = False
            self.query = None
            self.top_k = None

    expansion_capture = ExpansionCapture()

    async def fake_perform_query_expansion_search(query, mentions=None, top_k=5, num_expansions=3):
        expansion_capture.called = True
        expansion_capture.query = query
        expansion_capture.top_k = top_k
        assert mentions == requests_mentions
        return [
            {
                "id": "mention-doc",
                "score": 0.9,
                "payload": {"file_id": "file-a", "chunk_index": 0, "text": "expansion best"},
                "key": "file-a:0",
            },
            {
                "id": "exp-doc-2",
                "score": 0.3,
                "payload": {"file_id": "file-b", "chunk_index": 1, "text": "secondary"},
                "key": "file-b:1",
            },
        ]

    requests_mentions = mentions
    monkeypatch.setattr(chat_service, "query_documents_by_meeting_id", fake_meeting_query)
    monkeypatch.setattr(chat_service, "perform_query_expansion_search", fake_perform_query_expansion_search)

    results = await chat_service.query_documents_for_mentions(mentions, content="Need summary", top_k=2)

    assert expansion_capture.called is True
    assert expansion_capture.query == "Need summary"
    assert expansion_capture.top_k == 2
    assert len(results) == 2
    assert results[0]["payload"]["text"] == "expansion best"
    assert {doc["key"] for doc in results} == {"file-a:0", "file-b:1"}


@pytest.mark.asyncio
async def test_query_documents_for_mentions_skips_expansion_when_disabled(monkeypatch):
    mentions = [Mention(entity_type="meeting", entity_id="meeting-123", offset_start=0, offset_end=10)]

    async def fake_meeting_query(entity_id: str, top_k: int = 5, **_kwargs):
        return [
            {
                "id": "mention-doc",
                "score": 0.6,
                "payload": {"file_id": "file-a", "chunk_index": 0, "text": "meeting note"},
                "key": "file-a:0",
            }
        ]

    expansion_called = {"value": False}

    async def fake_perform_query_expansion_search(*_args, **_kwargs):
        expansion_called["value"] = True
        return []

    monkeypatch.setattr(chat_service, "query_documents_by_meeting_id", fake_meeting_query)
    monkeypatch.setattr(chat_service, "perform_query_expansion_search", fake_perform_query_expansion_search)

    results = await chat_service.query_documents_for_mentions(
        mentions,
        content="Need summary",
        include_query_expansion=False,
    )

    assert expansion_called["value"] is False
    assert len(results) == 1
    assert results[0]["payload"]["text"] == "meeting note"


@pytest.mark.asyncio
async def test_query_documents_by_project_id_builds_filter(monkeypatch):
    captured = {}

    class FakeClient:
        def __init__(self):
            self._called = False

        def scroll(self, collection_name, limit, offset, with_payload, with_vectors, scroll_filter):
            captured["collection_name"] = collection_name
            captured["limit"] = limit
            captured["offset"] = offset
            captured["with_payload"] = with_payload
            captured["with_vectors"] = with_vectors
            captured["filter"] = scroll_filter

            if self._called:
                return ([], None)

            self._called = True
            point = types.SimpleNamespace(
                id="point-1",
                payload={"project_id": "project-456", "text": "stub"},
            )
            return ([point], None)

    monkeypatch.setattr(qdrant_service, "get_qdrant_client", lambda: FakeClient())

    docs = await qdrant_service.query_documents_by_project_id("project-456", collection_name="custom_collection", top_k=2)

    assert len(docs) == 1
    assert captured["collection_name"] == "custom_collection"
    assert captured["limit"] == 2
    assert captured["with_payload"] is True
    assert captured["with_vectors"] is False
    filter_condition: qmodels.Filter = captured["filter"]
    assert isinstance(filter_condition, qmodels.Filter)
    assert filter_condition.must[0].key == "project_id"
    assert filter_condition.must[0].match.value == "project-456"


@pytest.mark.asyncio
async def test_query_documents_by_file_id_builds_filter(monkeypatch):
    captured = {}

    class FakeClient:
        def scroll(self, collection_name, limit, offset, with_payload, with_vectors, scroll_filter):
            captured["collection_name"] = collection_name
            captured["limit"] = limit
            captured["filter"] = scroll_filter

            point = types.SimpleNamespace(
                id="point-1",
                payload={"file_id": "file-123", "text": "stub"},
            )
            return ([point], None)

    monkeypatch.setattr(qdrant_service, "get_qdrant_client", lambda: FakeClient())

    docs = await qdrant_service.query_documents_by_file_id("file-123", top_k=3)

    assert len(docs) == 1
    assert captured["limit"] == 3
    filter_condition: qmodels.Filter = captured["filter"]
    assert isinstance(filter_condition, qmodels.Filter)
    assert filter_condition.must[0].key == "file_id"
    assert filter_condition.must[0].match.value == "file-123"


@pytest.mark.asyncio
async def test_perform_query_expansion_cache_hit_and_batch_embed(monkeypatch):
    cached_variants = ["Test cache query", "variant a"]

    class FakeRedis:
        def __init__(self):
            self.set_called = False

        async def get(self, key):
            self.key = key
            return json.dumps(cached_variants)

        async def set(self, *args, **kwargs):
            self.set_called = True

    fake_redis = FakeRedis()

    async def fake_get_async_redis_client():
        return fake_redis

    async def fake_expand_query_with_llm(*_args, **_kwargs):
        raise AssertionError("expand_query_with_llm should not run when cache hits")

    embed_calls = {}

    async def fake_embed_documents(variants):
        embed_calls["variants"] = list(variants)
        return [[0.1 + idx] for idx, _ in enumerate(variants)]

    async def fake_semantic_search_with_filters(query, top_k=5, meeting_ids=None, project_ids=None, file_ids=None, query_vector=None):
        assert query_vector is not None
        return [
            {
                "id": f"{query}-doc",
                "score": query_vector[0],
                "payload": {"file_id": "docs", "chunk_index": 0, "text": query},
                "vector": [],
            }
        ]

    monkeypatch.setattr(chat_service, "get_async_redis_client", fake_get_async_redis_client)
    monkeypatch.setattr(chat_service, "expand_query_with_llm", fake_expand_query_with_llm)
    monkeypatch.setattr(chat_service, "embed_documents", fake_embed_documents)
    monkeypatch.setattr(qdrant_service, "semantic_search_with_filters", fake_semantic_search_with_filters)

    results = await chat_service.perform_query_expansion_search("Test cache query", mentions=None, top_k=3, num_expansions=3)

    assert embed_calls["variants"] == cached_variants
    assert results and results[0]["key"] == "docs:0"
    assert not fake_redis.set_called


@pytest.mark.asyncio
async def test_perform_query_expansion_dedupe_keeps_best_score(monkeypatch):
    class FakeRedis:
        def __init__(self):
            self.stored = None

        async def get(self, _):
            return None

        async def set(self, _key, value, ex=None):
            self.stored = json.loads(value)

    fake_redis = FakeRedis()

    async def fake_get_async_redis_client():
        return fake_redis

    async def fake_expand_query_with_llm(*_args, **_kwargs):
        return ["primary"]

    async def fake_embed_documents(variants):
        return [[0.3] for _ in variants]

    async def fake_semantic_search_with_filters(query, top_k=5, meeting_ids=None, project_ids=None, file_ids=None, query_vector=None):
        return [
            {
                "id": "doc-low",
                "score": 0.3,
                "payload": {"file_id": "file-x", "chunk_index": 2, "text": "low"},
                "vector": [],
            },
            {
                "id": "doc-high",
                "score": 0.9,
                "payload": {"file_id": "file-x", "chunk_index": 2, "text": "high"},
                "vector": [],
            },
            {
                "id": "doc-other",
                "score": 0.6,
                "payload": {"file_id": "file-y", "chunk_index": 1, "text": "other"},
                "vector": [],
            },
        ]

    monkeypatch.setattr(chat_service, "get_async_redis_client", fake_get_async_redis_client)
    monkeypatch.setattr(chat_service, "expand_query_with_llm", fake_expand_query_with_llm)
    monkeypatch.setattr(chat_service, "embed_documents", fake_embed_documents)
    monkeypatch.setattr(qdrant_service, "semantic_search_with_filters", fake_semantic_search_with_filters)

    results = await chat_service.perform_query_expansion_search("needs dedupe", mentions=None, top_k=5, num_expansions=1)

    assert fake_redis.stored == ["primary"]
    assert len(results) == 2
    assert results[0]["payload"]["text"] == "high"
    assert results[0]["score"] == pytest.approx(0.9)
    assert results[0]["key"] == "file-x:2"
    assert results[1]["key"] == "file-y:1"


def test_process_chat_message_optimizer_selects_top_contexts(monkeypatch):
    from app.jobs import tasks
    from agno.models.message import Message

    captured = {}

    class DummyAgent:
        def run(self, prompt, history):
            captured["prompt"] = prompt
            captured["history"] = history
            return types.SimpleNamespace(content="assistant reply")

    class DummySession:
        def __init__(self):
            self.user_message = types.SimpleNamespace(
                id="msg-1",
                mentions=[
                    {
                        "entity_type": "meeting",
                        "entity_id": "M1",
                        "offset_start": 0,
                        "offset_end": 1,
                    }
                ],
            )
            self.added = []

        def query(self, model):
            class _Query:
                def __init__(self, result):
                    self._result = result

                def filter(self, *args, **kwargs):
                    return self

                def first(self):
                    return self._result

            return _Query(self.user_message)

        def add(self, obj):
            self.added.append(obj)

        def commit(self):
            pass

        def refresh(self, obj):
            obj.id = "ai-msg"
            obj.created_at = types.SimpleNamespace(isoformat=lambda: "2025-10-21T00:00:00Z")

        def close(self):
            pass

    def fake_session_local():
        return DummySession()

    async def fake_optimize_contexts_with_llm(*, query, history, context_block, desired_count=3):
        captured["optimizer_request"] = {
            "query": query,
            "history": history,
            "context_block": context_block,
            "desired_count": desired_count,
        }
        return json.dumps({"selected": [{"id": "file-a:0"}]})

    def fake_create_agent(*_args, **_kwargs):
        agent = DummyAgent()
        captured["agent"] = agent
        return agent

    def fake_get_agno_db():
        return None

    def fake_fetch_history(_conversation_id, limit=10):
        return [Message(role="user", content="previous note")]

    class FakeRedisPublisher:
        def publish(self, *_args, **_kwargs):
            captured["publish_called"] = True

    monkeypatch.setattr(tasks, "SessionLocal", fake_session_local)
    monkeypatch.setattr(tasks, "optimize_contexts_with_llm", fake_optimize_contexts_with_llm)
    monkeypatch.setattr(tasks, "create_general_chat_agent", fake_create_agent)
    monkeypatch.setattr(tasks, "get_agno_postgres_db", fake_get_agno_db)
    monkeypatch.setattr(tasks, "fetch_conversation_history_sync", fake_fetch_history)

    class FakeChatMessage:
        id = "id_field"

        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

    class FakeChatMessageType:
        def __init__(self):
            self.agent = "agent"
            self.user = "user"

    monkeypatch.setattr(tasks, "sync_redis_client", FakeRedisPublisher())
    monkeypatch.setattr(tasks, "ChatMessage", FakeChatMessage)
    monkeypatch.setattr(tasks, "ChatMessageType", FakeChatMessageType())

    query_results = [
        {"id": "mention-1", "score": 0.8, "payload": {"file_id": "file-m", "chunk_index": 2, "text": "mention doc"}, "key": "file-m:2"},
        {"id": "exp-1", "score": 0.9, "payload": {"file_id": "file-a", "chunk_index": 0, "text": "expansion doc"}, "key": "file-a:0"},
        {"id": "exp-2", "score": 0.5, "payload": {"file_id": "file-b", "chunk_index": 1, "text": "less relevant"}, "key": "file-b:1"},
    ]

    result = tasks.process_chat_message(
        conversation_id="conv-1",
        user_message_id="msg-1",
        content="How was the meeting?",
        user_id="user-1",
        query_results=query_results,
    )

    assert result["status"] == "success"
    assert "expansion doc" in captured["prompt"]
    assert "mention doc" not in captured["prompt"]
    assert any("previous note" in line.content for line in captured["history"])
    optimizer_request = captured["optimizer_request"]
    assert optimizer_request["query"] == "How was the meeting?"
    assert "previous note" in optimizer_request["history"]
    assert "file-a:0" in optimizer_request["context_block"]
    assert optimizer_request["desired_count"] == 3


def test_process_chat_message_optimizer_fallback(monkeypatch):
    from app.jobs import tasks
    from agno.models.message import Message

    captured = {}

    class DummyAgent:
        def run(self, prompt, history):
            captured["prompt"] = prompt
            return types.SimpleNamespace(content="assistant reply")

    class DummySession:
        def __init__(self):
            self.user_message = types.SimpleNamespace(
                id="msg-2",
                mentions=[
                    {
                        "entity_type": "meeting",
                        "entity_id": "M2",
                        "offset_start": 0,
                        "offset_end": 1,
                    }
                ],
            )

        def query(self, model):
            class _Query:
                def __init__(self, result):
                    self._result = result

                def filter(self, *args, **kwargs):
                    return self

                def first(self):
                    return self._result

            return _Query(self.user_message)

        def add(self, _obj):
            pass

        def commit(self):
            pass

        def refresh(self, obj):
            obj.id = "ai-msg"
            obj.created_at = types.SimpleNamespace(isoformat=lambda: "2025-10-21T00:00:00Z")

        def close(self):
            pass

    def fake_session_local():
        return DummySession()

    async def fake_optimize_contexts_with_llm(*_args, **_kwargs):
        return None

    def fake_create_agent(*_args, **_kwargs):
        return DummyAgent()

    monkeypatch.setattr(tasks, "SessionLocal", fake_session_local)
    monkeypatch.setattr(tasks, "optimize_contexts_with_llm", fake_optimize_contexts_with_llm)
    monkeypatch.setattr(tasks, "create_general_chat_agent", fake_create_agent)
    monkeypatch.setattr(tasks, "get_agno_postgres_db", lambda: None)
    monkeypatch.setattr(tasks, "fetch_conversation_history_sync", lambda *_args, **_kwargs: [Message(role="user", content="history")])

    class FakeChatMessage:
        id = "id_field"

        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

    class FakeChatMessageType:
        def __init__(self):
            self.agent = "agent"
            self.user = "user"

    monkeypatch.setattr(tasks, "sync_redis_client", types.SimpleNamespace(publish=lambda *a, **k: None))
    monkeypatch.setattr(tasks, "ChatMessage", FakeChatMessage)
    monkeypatch.setattr(tasks, "ChatMessageType", FakeChatMessageType())

    query_results = [
        {"id": "mention-1", "score": 0.8, "payload": {"file_id": "file-m", "chunk_index": 2, "text": "mention doc"}, "key": "file-m:2"},
        {"id": "exp-1", "score": 0.9, "payload": {"file_id": "file-z", "chunk_index": 0, "text": "expansion doc"}, "key": "file-z:0"},
    ]

    tasks.process_chat_message(
        conversation_id="conv-2",
        user_message_id="msg-2",
        content="Provide highlights",
        user_id="user-2",
        query_results=query_results,
    )

    prompt_text = captured["prompt"]
    assert "mention doc" in prompt_text
    assert "expansion doc" in prompt_text


@pytest.mark.asyncio
async def test_optimize_contexts_with_llm_validates_response(monkeypatch):
    from app.utils import llm as llm_utils

    captured = {}

    async def fake_chat_complete(system_prompt, user_prompt):
        captured["system_prompt"] = system_prompt
        captured["user_prompt"] = user_prompt
        return '[{"id": "doc-1", "reason": "matching"}]'

    monkeypatch.setattr(llm_utils, "chat_complete", fake_chat_complete)

    result = await llm_utils.optimize_contexts_with_llm(
        query="Tổng hợp nội dung",
        history="assistant: hi",
        context_block="doc-1 | score=0.9 | text=ghi chú",
        desired_count=2,
    )

    assert result == '[{"id": "doc-1", "reason": "matching"}]'
    assert "{desired_count}" not in captured["system_prompt"]
    assert "2" in captured["system_prompt"]
    assert "Tổng hợp nội dung" in captured["user_prompt"]
    assert "ghi chú" in captured["user_prompt"]


@pytest.mark.asyncio
async def test_optimize_contexts_with_llm_invalid_json(monkeypatch):
    from app.utils import llm as llm_utils

    async def fake_chat_complete(system_prompt, user_prompt):
        return "not-json"

    monkeypatch.setattr(llm_utils, "chat_complete", fake_chat_complete)

    result = await llm_utils.optimize_contexts_with_llm(
        query="Anything",
        history="user: hi",
        context_block="doc",
        desired_count=1,
    )

    assert result is None
