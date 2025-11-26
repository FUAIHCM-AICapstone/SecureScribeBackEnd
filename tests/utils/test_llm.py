"""Unit tests for LLM utility functions"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from faker import Faker

fake = Faker()


class TestEmbedQuery:
    """Tests for embed_query function"""

    @pytest.mark.asyncio
    async def test_embed_query_success(self):
        """Test embedding a single query"""
        from app.utils.llm import embed_query

        mock_embeddings = MagicMock()
        mock_vector = [0.1, 0.2, 0.3, 0.4, 0.5]
        mock_embeddings.embed.return_value = mock_vector

        with patch("app.utils.llm._get_embeddings", return_value=mock_embeddings):
            query = fake.sentence()
            result = await embed_query(query)

            assert isinstance(result, list)
            assert len(result) == len(mock_vector)
            assert all(isinstance(x, (int, float)) for x in result)
            mock_embeddings.embed.assert_called_once_with(query)

    @pytest.mark.asyncio
    async def test_embed_query_empty_string(self):
        """Test embedding an empty query"""
        from app.utils.llm import embed_query

        mock_embeddings = MagicMock()
        mock_embeddings.embed.return_value = [0.0] * 768

        with patch("app.utils.llm._get_embeddings", return_value=mock_embeddings):
            result = await embed_query("")

            assert isinstance(result, list)
            mock_embeddings.embed.assert_called_once_with("")

    @pytest.mark.asyncio
    async def test_embed_query_long_text(self):
        """Test embedding long text query"""
        from app.utils.llm import embed_query

        mock_embeddings = MagicMock()
        mock_vector = [0.1] * 768
        mock_embeddings.embed.return_value = mock_vector

        with patch("app.utils.llm._get_embeddings", return_value=mock_embeddings):
            long_query = " ".join([fake.word() for _ in range(500)])
            result = await embed_query(long_query)

            assert isinstance(result, list)
            assert len(result) == 768
            mock_embeddings.embed.assert_called_once()


class TestEmbedDocuments:
    """Tests for embed_documents function"""

    @pytest.mark.asyncio
    async def test_embed_documents_success(self):
        """Test embedding multiple documents"""
        from app.utils.llm import embed_documents

        num_docs = 5
        docs = [fake.paragraph() for _ in range(num_docs)]
        mock_embeddings = MagicMock()
        mock_vectors = [[0.1] * 768 for _ in range(num_docs)]
        mock_embeddings.embed_batch.return_value = mock_vectors

        with patch("app.utils.llm._get_embeddings", return_value=mock_embeddings):
            result = await embed_documents(docs)

            assert isinstance(result, list)
            assert len(result) == num_docs
            assert all(isinstance(v, list) for v in result)
            assert all(len(v) == 768 for v in result)
            mock_embeddings.embed_batch.assert_called_once_with(docs)

    @pytest.mark.asyncio
    async def test_embed_documents_empty_list(self):
        """Test embedding empty document list"""
        from app.utils.llm import embed_documents

        result = await embed_documents([])

        assert isinstance(result, list)
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_embed_documents_single_doc(self):
        """Test embedding a single document"""
        from app.utils.llm import embed_documents

        docs = [fake.paragraph()]
        mock_embeddings = MagicMock()
        mock_vectors = [[0.1] * 768]
        mock_embeddings.embed_batch.return_value = mock_vectors

        with patch("app.utils.llm._get_embeddings", return_value=mock_embeddings):
            result = await embed_documents(docs)

            assert isinstance(result, list)
            assert len(result) == 1
            mock_embeddings.embed_batch.assert_called_once_with(docs)

    @pytest.mark.asyncio
    async def test_embed_documents_large_batch(self):
        """Test embedding large batch of documents"""
        from app.utils.llm import embed_documents

        num_docs = 100
        docs = [fake.paragraph() for _ in range(num_docs)]
        mock_embeddings = MagicMock()
        mock_vectors = [[0.1] * 768 for _ in range(num_docs)]
        mock_embeddings.embed_batch.return_value = mock_vectors

        with patch("app.utils.llm._get_embeddings", return_value=mock_embeddings):
            result = await embed_documents(docs)

            assert len(result) == num_docs


class TestChatComplete:
    """Tests for chat_complete function"""

    @pytest.mark.asyncio
    async def test_chat_complete_success(self):
        """Test basic chat completion"""
        from app.utils.llm import chat_complete

        system_prompt = "Bạn là một trợ lý thông minh"
        user_prompt = fake.sentence()
        expected_response = fake.paragraph()

        mock_model = AsyncMock()
        mock_message = MagicMock()
        mock_message.content = expected_response
        mock_model.ainvoke.return_value = mock_message

        with patch("app.utils.llm._get_model", return_value=mock_model):
            result = await chat_complete(system_prompt, user_prompt)

            assert result == expected_response
            assert mock_model.ainvoke.called

    @pytest.mark.asyncio
    async def test_chat_complete_empty_system_prompt(self):
        """Test chat completion with empty system prompt"""
        from app.utils.llm import chat_complete

        mock_model = AsyncMock()
        mock_message = MagicMock()
        mock_message.content = "Response"
        mock_model.ainvoke.return_value = mock_message

        with patch("app.utils.llm._get_model", return_value=mock_model):
            result = await chat_complete("", fake.sentence())

            assert isinstance(result, str)
            mock_model.ainvoke.assert_called_once()

    @pytest.mark.asyncio
    async def test_chat_complete_empty_user_prompt(self):
        """Test chat completion with empty user prompt"""
        from app.utils.llm import chat_complete

        mock_model = AsyncMock()
        mock_message = MagicMock()
        mock_message.content = "Response"
        mock_model.ainvoke.return_value = mock_message

        with patch("app.utils.llm._get_model", return_value=mock_model):
            result = await chat_complete(fake.sentence(), "")

            assert isinstance(result, str)


class TestOptimizeContextsWithLLM:
    """Tests for optimize_contexts_with_llm function"""

    @pytest.mark.asyncio
    async def test_optimize_contexts_success(self):
        """Test context optimization with valid response"""
        from app.utils.llm import optimize_contexts_with_llm

        query = fake.sentence()
        history = fake.paragraph()
        context_block = "[{id: 1}, {id: 2}]"
        expected_response = '[{"id": "file1:chunk2", "reason": "phân tích lỗi"}]'

        with patch(
            "app.utils.llm.chat_complete",
            return_value=expected_response,
        ) as mock_chat:
            result = await optimize_contexts_with_llm(query, history, context_block)

            assert result == expected_response
            mock_chat.assert_called_once()

    @pytest.mark.asyncio
    async def test_optimize_contexts_invalid_json(self):
        """Test context optimization with invalid JSON response"""
        from app.utils.llm import optimize_contexts_with_llm

        with patch(
            "app.utils.llm.chat_complete",
            return_value="not valid json",
        ):
            result = await optimize_contexts_with_llm(
                fake.sentence(),
                fake.paragraph(),
                "[{id: 1}]",
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_optimize_contexts_empty_response(self):
        """Test context optimization with empty response"""
        from app.utils.llm import optimize_contexts_with_llm

        with patch("app.utils.llm.chat_complete", return_value=""):
            result = await optimize_contexts_with_llm(
                fake.sentence(),
                fake.paragraph(),
                "[{id: 1}]",
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_optimize_contexts_custom_desired_count(self):
        """Test context optimization with custom desired count"""
        from app.utils.llm import optimize_contexts_with_llm

        desired_count = 5
        expected_response = '[{"id": "file1:chunk1", "reason": "reason1"}]'

        with patch(
            "app.utils.llm.chat_complete",
            return_value=expected_response,
        ) as mock_chat:
            result = await optimize_contexts_with_llm(
                fake.sentence(),
                fake.paragraph(),
                "[{id: 1}]",
                desired_count=desired_count,
            )

            assert result == expected_response
            # Verify desired_count is passed in the prompt
            call_args = mock_chat.call_args[0]
            assert str(desired_count) in call_args[0]  # Check system_prompt

    @pytest.mark.asyncio
    async def test_optimize_contexts_llm_error(self):
        """Test context optimization when LLM call fails"""
        from app.utils.llm import optimize_contexts_with_llm

        with patch("app.utils.llm.chat_complete", side_effect=Exception("LLM Error")):
            result = await optimize_contexts_with_llm(
                fake.sentence(),
                fake.paragraph(),
                "[{id: 1}]",
            )

            assert result is None


class TestExpandQueryWithLLM:
    """Tests for expand_query_with_llm function"""

    @pytest.mark.asyncio
    async def test_expand_query_success(self):
        """Test query expansion with valid response"""
        from app.utils.llm import expand_query_with_llm

        query = "tìm lỗi Redis"
        expanded_queries = [
            "tìm lỗi Redis",
            "vấn đề connection Redis",
            "Redis timeout error",
        ]
        response = "\n".join(expanded_queries)

        with patch("app.utils.llm.chat_complete", return_value=response):
            result = await expand_query_with_llm(query, num_expansions=3)

            assert isinstance(result, list)
            assert len(result) >= 1
            assert query in result or any(q in expanded_queries for q in result)

    @pytest.mark.asyncio
    async def test_expand_query_default_expansions(self):
        """Test query expansion with default expansion count"""
        from app.utils.llm import expand_query_with_llm

        query = fake.sentence()
        response = "\n".join([fake.sentence() for _ in range(3)])

        with patch("app.utils.llm.chat_complete", return_value=response):
            result = await expand_query_with_llm(query)

            assert isinstance(result, list)
            assert len(result) >= 1

    @pytest.mark.asyncio
    async def test_expand_query_fallback_on_error(self):
        """Test query expansion falls back to original on error"""
        from app.utils.llm import expand_query_with_llm

        query = fake.sentence()

        with patch("app.utils.llm.chat_complete", side_effect=Exception("Error")):
            result = await expand_query_with_llm(query)

            assert isinstance(result, list)
            assert len(result) == 1
            assert result[0] == query

    @pytest.mark.asyncio
    async def test_expand_query_empty_response(self):
        """Test query expansion with empty LLM response"""
        from app.utils.llm import expand_query_with_llm

        query = fake.sentence()

        with patch("app.utils.llm.chat_complete", return_value=""):
            result = await expand_query_with_llm(query)

            assert isinstance(result, list)
            assert len(result) >= 1

    @pytest.mark.asyncio
    async def test_expand_query_custom_expansion_count(self):
        """Test query expansion with custom expansion count"""
        from app.utils.llm import expand_query_with_llm

        query = fake.sentence()
        num_expansions = 5
        response = "\n".join([fake.sentence() for _ in range(num_expansions)])

        with patch("app.utils.llm.chat_complete", return_value=response) as mock_chat:
            result = await expand_query_with_llm(query, num_expansions=num_expansions)

            assert isinstance(result, list)
            # Verify num_expansions is passed in prompt
            call_args = mock_chat.call_args[0]
            assert str(num_expansions) in call_args[1]


class TestCreateGeneralChatAgent:
    """Tests for create_general_chat_agent function"""

    def test_create_general_chat_agent_success(self):
        """Test creating a general chat agent"""
        from app.utils.llm import create_general_chat_agent

        mock_db = MagicMock()
        session_id = fake.uuid4()
        user_id = fake.uuid4()

        with patch("app.utils.llm.Agent") as mock_agent_class:
            mock_agent = MagicMock()
            mock_agent_class.return_value = mock_agent

            agent = create_general_chat_agent(mock_db, session_id, user_id)

            assert agent is mock_agent
            mock_agent_class.assert_called_once()
            call_kwargs = mock_agent_class.call_args[1]
            assert call_kwargs["name"] == "General Chat Assistant"
            assert call_kwargs["session_id"] == session_id
            assert call_kwargs["user_id"] == user_id

    def test_create_general_chat_agent_properties(self):
        """Test created agent has correct properties"""
        from app.utils.llm import create_general_chat_agent

        mock_db = MagicMock()
        session_id = fake.uuid4()
        user_id = fake.uuid4()

        with patch("app.utils.llm.Agent") as mock_agent_class:
            mock_agent = MagicMock()
            mock_agent_class.return_value = mock_agent

            agent = create_general_chat_agent(mock_db, session_id, user_id)

            mock_agent_class.assert_called_once()
            call_kwargs = mock_agent_class.call_args[1]
            assert call_kwargs["enable_user_memories"] is True
            assert call_kwargs["enable_session_summaries"] is True
            assert call_kwargs["add_history_to_context"] is True
            assert call_kwargs["num_history_runs"] == 20
            assert call_kwargs["markdown"] is True

    def test_create_general_chat_agent_with_different_sessions(self):
        """Test creating agents with different session IDs"""
        from app.utils.llm import create_general_chat_agent

        mock_db = MagicMock()
        user_id = fake.uuid4()

        with patch("app.utils.llm.Agent") as mock_agent_class:
            mock_agent1 = MagicMock()
            mock_agent2 = MagicMock()
            mock_agent_class.side_effect = [mock_agent1, mock_agent2]

            session_id_1 = fake.uuid4()
            session_id_2 = fake.uuid4()

            agent1 = create_general_chat_agent(mock_db, session_id_1, user_id)
            agent2 = create_general_chat_agent(mock_db, session_id_2, user_id)

            assert agent1 is mock_agent1
            assert agent2 is mock_agent2

            calls = mock_agent_class.call_args_list
            assert calls[0][1]["session_id"] == session_id_1
            assert calls[1][1]["session_id"] == session_id_2
            assert calls[0][1]["user_id"] == calls[1][1]["user_id"] == user_id


class TestGetAgnoPostgresDb:
    """Tests for get_agno_postgres_db function"""

    def test_get_agno_postgres_db_success(self):
        """Test getting PostgresDb instance"""
        from app.utils.llm import get_agno_postgres_db

        with patch("app.utils.llm.PostgresDb") as mock_postgres_db:
            db = get_agno_postgres_db()

            assert mock_postgres_db.called
            mock_postgres_db.assert_called_once()

    def test_get_agno_postgres_db_configuration(self):
        """Test PostgresDb configuration"""
        from app.utils.llm import get_agno_postgres_db

        with patch("app.utils.llm.PostgresDb") as mock_postgres_db:
            db = get_agno_postgres_db()

            # Verify PostgresDb was called with correct parameters
            call_kwargs = mock_postgres_db.call_args[1]
            assert "db_url" in call_kwargs
            assert "session_table" in call_kwargs
            assert "memory_table" in call_kwargs
            assert call_kwargs["session_table"] == "conversations"
            assert call_kwargs["memory_table"] == "chat_messages"
