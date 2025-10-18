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
