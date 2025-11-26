"""Unit tests for chat service functions"""

import json
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from faker import Faker
from sqlalchemy.orm import Session

from app.schemas.chat import Mention
from app.services.chat import (
    _merge_context_candidates,
    create_chat_message,
    perform_query_expansion_search,
    query_documents_for_mentions,
)
from tests.factories import ConversationFactory, UserFactory

fake = Faker()


class TestCreateChatMessage:
    """Tests for create_chat_message function"""

    def test_create_chat_message_success(self, db_session: Session):
        """Test creating a chat message successfully"""
        user = UserFactory.create(db_session)
        conversation = ConversationFactory.create(db_session, user)
        db_session.commit()

        message = create_chat_message(db=db_session, conversation_id=conversation.id, user_id=user.id, content="Test message", message_type="user")

        assert message is not None
        assert message.conversation_id == conversation.id
        assert message.content == "Test message"
        assert message.message_type == "user"

    def test_create_chat_message_conversation_not_found(self, db_session: Session):
        """Test creating message for non-existent conversation"""
        user = UserFactory.create(db_session)
        fake_conversation_id = uuid.uuid4()

        message = create_chat_message(db=db_session, conversation_id=fake_conversation_id, user_id=user.id, content="Test message", message_type="user")

        assert message is None

    def test_create_chat_message_no_access(self, db_session: Session):
        """Test creating message without conversation access"""
        user1 = UserFactory.create(db_session)
        user2 = UserFactory.create(db_session)
        conversation = ConversationFactory.create(db_session, user1)
        db_session.commit()

        message = create_chat_message(db=db_session, conversation_id=conversation.id, user_id=user2.id, content="Test message", message_type="user")

        assert message is None

    def test_create_chat_message_with_mentions(self, db_session: Session):
        """Test creating message with mentions"""
        user = UserFactory.create(db_session)
        conversation = ConversationFactory.create(db_session, user)

        mentions = [{"entity_type": "meeting", "entity_id": str(uuid.uuid4())}, {"entity_type": "project", "entity_id": str(uuid.uuid4())}]

        message = create_chat_message(db=db_session, conversation_id=conversation.id, user_id=user.id, content="Test message", message_type="user", mentions=mentions)

        assert message is not None
        assert message.mentions == mentions


class TestMergeContextCandidates:
    """Tests for _merge_context_candidates function"""

    def test_merge_context_candidates_basic(self):
        """Test basic merging of context candidates"""
        candidates = [{"payload": {"file_id": "file1", "chunk_index": 0, "text": "Test 1"}, "score": 0.9, "id": "doc1"}, {"payload": {"file_id": "file1", "chunk_index": 0, "text": "Test 1"}, "score": 0.8, "id": "doc1"}, {"payload": {"file_id": "file2", "chunk_index": 1, "text": "Test 2"}, "score": 0.7, "id": "doc2"}]

        result = _merge_context_candidates(candidates, limit=10)

        # Should deduplicate file1/chunk0 and keep higher score
        assert len(result) == 2
        assert result[0]["score"] == 0.9  # Higher score kept
        assert result[0]["payload"]["file_id"] == "file1"

    def test_merge_context_candidates_limit(self):
        """Test merging with limit"""
        candidates = [{"payload": {"file_id": f"file{i}"}, "score": 0.5 + i * 0.1, "id": f"doc{i}"} for i in range(5)]

        result = _merge_context_candidates(candidates, limit=3)

        assert len(result) == 3
        # Should be sorted by score descending
        assert result[0]["score"] > result[1]["score"] > result[2]["score"]

    def test_merge_context_candidates_empty(self):
        """Test merging empty candidates"""
        result = _merge_context_candidates([], limit=10)
        assert result == []

    def test_merge_context_candidates_fallback_dedupe(self):
        """Test fallback deduplication when file_id/chunk_index not available"""
        candidates = [
            {"payload": {"text": "Test"}, "score": 0.9, "id": "doc1"},
            {"payload": {"text": "Test"}, "score": 0.8, "id": "doc1"},
        ]

        result = _merge_context_candidates(candidates, limit=10)

        # Should deduplicate by id
        assert len(result) == 1
        assert result[0]["score"] == 0.9  # Higher score kept


class TestQueryDocumentsForMentions:
    """Tests for query_documents_for_mentions function"""

    @pytest.mark.asyncio
    async def test_query_documents_for_mentions_meeting(self, db_session: Session):
        """Test querying documents for meeting mentions"""
        user = UserFactory.create(db_session)
        meeting_id = str(uuid.uuid4())

        mentions = [Mention(entity_type="meeting", entity_id=meeting_id, offset_start=0, offset_end=10)]

        with patch("app.services.qdrant_service.query_documents_by_meeting_id", new_callable=AsyncMock) as mock_query:
            mock_query.return_value = [{"id": "doc1", "score": 0.9, "payload": {"text": "Meeting content"}}]

            result = await query_documents_for_mentions(mentions=mentions, current_user_id=str(user.id), db=db_session)

            assert len(result) == 1
            assert result[0]["id"] == "doc1"
            mock_query.assert_called_once_with(meeting_id, top_k=5, db=db_session, user_id=str(user.id))

    @pytest.mark.asyncio
    async def test_query_documents_for_mentions_project(self, db_session: Session):
        """Test querying documents for project mentions"""
        user = UserFactory.create(db_session)
        project_id = str(uuid.uuid4())

        mentions = [Mention(entity_type="project", entity_id=project_id, offset_start=0, offset_end=10)]

        with patch("app.services.qdrant_service.query_documents_by_project_id", new_callable=AsyncMock) as mock_query:
            mock_query.return_value = [{"id": "doc1", "score": 0.8, "payload": {"text": "Project content"}}]

            result = await query_documents_for_mentions(mentions=mentions, current_user_id=str(user.id), db=db_session)

            assert len(result) == 1
            mock_query.assert_called_once_with(project_id, top_k=5, db=db_session, user_id=str(user.id))

    @pytest.mark.asyncio
    async def test_query_documents_for_mentions_file(self, db_session: Session):
        """Test querying documents for file mentions"""
        user = UserFactory.create(db_session)
        file_id = str(uuid.uuid4())

        mentions = [Mention(entity_type="file", entity_id=file_id, offset_start=0, offset_end=10)]

        with patch("app.services.qdrant_service.query_documents_by_file_id", new_callable=AsyncMock) as mock_query:
            mock_query.return_value = [{"id": "doc1", "score": 0.7, "payload": {"text": "File content"}}]

            result = await query_documents_for_mentions(mentions=mentions, current_user_id=str(user.id), db=db_session)

            assert len(result) == 1
            mock_query.assert_called_once_with(file_id, top_k=5, db=db_session, user_id=str(user.id))

    @pytest.mark.asyncio
    async def test_query_documents_for_mentions_multiple(self, db_session: Session):
        """Test querying documents for multiple mentions"""
        user = UserFactory.create(db_session)
        meeting_id = str(uuid.uuid4())
        project_id = str(uuid.uuid4())

        mentions = [Mention(entity_type="meeting", entity_id=meeting_id, offset_start=0, offset_end=10), Mention(entity_type="project", entity_id=project_id, offset_start=11, offset_end=20)]

        with patch("app.services.qdrant_service.query_documents_by_meeting_id", new_callable=AsyncMock) as mock_meeting_query, patch("app.services.qdrant_service.query_documents_by_project_id", new_callable=AsyncMock) as mock_project_query:
            mock_meeting_query.return_value = [{"id": "meeting_doc", "score": 0.9, "payload": {"text": "Meeting content"}}]
            mock_project_query.return_value = [{"id": "project_doc", "score": 0.8, "payload": {"text": "Project content"}}]

            result = await query_documents_for_mentions(mentions=mentions, current_user_id=str(user.id), db=db_session)

            assert len(result) == 2
            mock_meeting_query.assert_called_once()
            mock_project_query.assert_called_once()

    @pytest.mark.asyncio
    async def test_query_documents_for_mentions_with_expansion(self, db_session: Session):
        """Test querying documents with query expansion"""
        user = UserFactory.create(db_session)
        meeting_id = str(uuid.uuid4())

        mentions = [Mention(entity_type="meeting", entity_id=meeting_id, offset_start=0, offset_end=10)]

        with patch("app.services.qdrant_service.query_documents_by_meeting_id", new_callable=AsyncMock) as mock_query, patch("app.services.chat.perform_query_expansion_search", new_callable=AsyncMock) as mock_expansion:
            mock_query.return_value = [{"id": "mention_doc", "score": 0.9, "payload": {"text": "Mention content"}}]
            mock_expansion.return_value = [{"id": "expansion_doc", "score": 0.7, "payload": {"text": "Expansion content"}}]

            result = await query_documents_for_mentions(mentions=mentions, current_user_id=str(user.id), db=db_session, content="test query", include_query_expansion=True)

            # Should include both mention and expansion results
            assert len(result) >= 1
            mock_expansion.assert_called_once()

    @pytest.mark.asyncio
    async def test_query_documents_for_mentions_empty(self, db_session: Session):
        """Test querying documents with empty mentions"""
        user = UserFactory.create(db_session)

        result = await query_documents_for_mentions(mentions=[], current_user_id=str(user.id), db=db_session)

        assert result == []


class TestPerformQueryExpansionSearch:
    """Tests for perform_query_expansion_search function"""

    @pytest.mark.asyncio
    async def test_perform_query_expansion_search_success(self):
        """Test successful query expansion search"""
        query = "test query"

        with patch("app.services.chat.expand_query_with_llm") as mock_expand, patch("app.utils.redis.get_async_redis_client") as mock_redis, patch("app.utils.llm.embed_documents") as mock_embed, patch("app.services.qdrant_service.semantic_search_with_filters") as mock_search:
            # Mock Redis - no cached result
            mock_redis_client = AsyncMock()
            mock_redis_client.get.return_value = None
            mock_redis.return_value = mock_redis_client

            # Mock LLM expansion
            mock_expand.return_value = ["expanded query 1", "expanded query 2"]

            # Mock embeddings
            mock_embed.return_value = [[0.1, 0.2], [0.3, 0.4]]

            # Mock search results
            mock_search.return_value = [{"id": "doc1", "score": 0.9, "payload": {"text": "Result 1"}}, {"id": "doc2", "score": 0.8, "payload": {"text": "Result 2"}}]

            result = await perform_query_expansion_search(query)

            assert len(result) == 2
            mock_expand.assert_called_once_with(query, 3)
            mock_embed.assert_called_once()
            assert mock_search.call_count == 2  # Called for each expanded query

    @pytest.mark.asyncio
    async def test_perform_query_expansion_search_cached(self):
        """Test query expansion with cached results"""
        query = "test query"

        with patch("app.services.chat.expand_query_with_llm", new_callable=AsyncMock) as mock_expand, patch("app.utils.redis.get_async_redis_client") as mock_redis:
            # Mock Redis with cached result
            mock_redis_client = AsyncMock()
            mock_redis_client.get.return_value = json.dumps(["cached query 1", "cached query 2"])
            mock_redis.return_value = mock_redis_client

            result = await perform_query_expansion_search(query)

            # Should use cached results without calling LLM
            mock_expand.assert_not_called()
            assert len(result) == 0  # No search performed in this test

    @pytest.mark.asyncio
    async def test_perform_query_expansion_search_empty_query(self):
        """Test query expansion with empty query"""
        result = await perform_query_expansion_search("")
        assert result == []

    @pytest.mark.asyncio
    async def test_perform_query_expansion_search_no_expansions(self):
        """Test query expansion when LLM returns no expansions"""
        query = "test query"

        with patch("app.services.chat.expand_query_with_llm", new_callable=AsyncMock) as mock_expand:
            mock_expand.return_value = []

            result = await perform_query_expansion_search(query)

            assert result == []

    @pytest.mark.asyncio
    async def test_perform_query_expansion_search_with_mentions(self):
        """Test query expansion search with mentions"""
        query = "test query"
        mentions = [Mention(entity_type="meeting", entity_id=str(uuid.uuid4()), offset_start=0, offset_end=10)]

        with patch("app.services.chat.expand_query_with_llm") as mock_expand, patch("app.utils.redis.get_async_redis_client") as mock_redis, patch("app.utils.llm.embed_documents") as mock_embed, patch("app.services.qdrant_service.semantic_search_with_filters") as mock_search:
            # Mock Redis
            mock_redis_client = AsyncMock()
            mock_redis_client.get.return_value = None
            mock_redis.return_value = mock_redis_client

            # Mock expansions and embeddings
            mock_expand.return_value = ["expanded query"]
            mock_embed.return_value = [[0.1, 0.2]]

            # Mock search
            mock_search.return_value = [{"id": "doc1", "score": 0.9, "payload": {"text": "Result"}}]

            result = await perform_query_expansion_search(query, mentions=mentions)

            assert len(result) == 1
            # Verify mentions were passed to search
            mock_search.assert_called_once()
            call_args = mock_search.call_args
            assert call_args[1]["meeting_ids"] == [str(mentions[0].entity_id)]

    @pytest.mark.asyncio
    async def test_perform_query_expansion_search_exception_handling(self):
        """Test exception handling in query expansion search"""
        query = "test query"

        with patch("app.services.chat.expand_query_with_llm", side_effect=Exception("LLM error")):
            result = await perform_query_expansion_search(query)
            assert result == []
