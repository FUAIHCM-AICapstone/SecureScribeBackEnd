"""Unit tests for search service functions"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from app.services.qdrant_service import (
    delete_file_vectors,
    delete_transcript_vectors,
    process_file,
    query_documents_by_file_id,
    query_documents_by_meeting_id,
    query_documents_by_project_id,
    reindex_file,
    search_vectors,
    semantic_search_with_filters,
    update_file_vectors_metadata,
    upsert_vectors,
)
from tests.factories import FileFactory, MeetingFactory, ProjectFactory, UserFactory


class TestUpsertVectors:
    """Tests for upsert_vectors function"""

    @pytest.mark.asyncio
    @patch("app.services.qdrant_service.get_qdrant_client")
    async def test_upsert_vectors_success(self, mock_get_client):
        """Test upserting vectors successfully"""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        vectors = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        payloads = [{"text": "chunk1"}, {"text": "chunk2"}]

        result = await upsert_vectors("test_collection", vectors, payloads)

        assert result is True
        mock_client.upsert.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.services.qdrant_service.get_qdrant_client")
    async def test_upsert_vectors_empty(self, mock_get_client):
        """Test upserting empty vectors"""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        result = await upsert_vectors("test_collection", [], [])

        assert result is False
        mock_client.upsert.assert_not_called()

    @pytest.mark.asyncio
    @patch("app.services.qdrant_service.get_qdrant_client")
    async def test_upsert_vectors_exception(self, mock_get_client):
        """Test upserting vectors with exception"""
        mock_client = MagicMock()
        mock_client.upsert.side_effect = Exception("Connection error")
        mock_get_client.return_value = mock_client

        vectors = [[0.1, 0.2, 0.3]]
        payloads = [{"text": "chunk1"}]

        result = await upsert_vectors("test_collection", vectors, payloads)

        assert result is False


class TestSearchVectors:
    """Tests for search_vectors function"""

    @pytest.mark.asyncio
    @patch("app.services.qdrant_service.get_qdrant_client")
    async def test_search_vectors_success(self, mock_get_client):
        """Test searching vectors successfully"""
        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_result.points = [
            MagicMock(id="1", score=0.95, payload={"text": "result1"}),
            MagicMock(id="2", score=0.85, payload={"text": "result2"}),
        ]
        mock_client.query_points.return_value = mock_result
        mock_get_client.return_value = mock_client

        query_vector = [0.1, 0.2, 0.3]
        results = await search_vectors("test_collection", query_vector, top_k=5)

        assert len(results) == 2
        assert results[0].score == 0.95
        mock_client.query_points.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.services.qdrant_service.get_qdrant_client")
    async def test_search_vectors_empty_query(self, mock_get_client):
        """Test searching with empty query vector"""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        results = await search_vectors("test_collection", [], top_k=5)

        assert results == []
        mock_client.query_points.assert_not_called()

    @pytest.mark.asyncio
    @patch("app.services.qdrant_service.get_qdrant_client")
    async def test_search_vectors_with_filter(self, mock_get_client):
        """Test searching vectors with filter"""
        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_result.points = [MagicMock(id="1", score=0.95, payload={"text": "result1"})]
        mock_client.query_points.return_value = mock_result
        mock_get_client.return_value = mock_client

        query_vector = [0.1, 0.2, 0.3]
        query_filter = MagicMock()
        results = await search_vectors("test_collection", query_vector, top_k=5, query_filter=query_filter)

        assert len(results) == 1
        mock_client.query_points.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.services.qdrant_service.get_qdrant_client")
    async def test_search_vectors_exception(self, mock_get_client):
        """Test searching vectors with exception"""
        mock_client = MagicMock()
        mock_client.query_points.side_effect = Exception("Search error")
        mock_get_client.return_value = mock_client

        query_vector = [0.1, 0.2, 0.3]
        results = await search_vectors("test_collection", query_vector, top_k=5)

        assert results == []


class TestSemanticSearchWithFilters:
    """Tests for semantic_search_with_filters function"""

    @pytest.mark.asyncio
    @patch("app.services.qdrant_service.search_vectors")
    @patch("app.utils.llm.embed_query")
    async def test_semantic_search_success(self, mock_embed_query, mock_search_vectors):
        """Test semantic search successfully"""
        mock_embed_query.return_value = [0.1, 0.2, 0.3]
        mock_search_vectors.return_value = [
            MagicMock(id="1", score=0.95, payload={"text": "result1"}, vector=[0.1, 0.2, 0.3]),
        ]

        results = await semantic_search_with_filters("test query", top_k=5)

        assert len(results) == 1
        assert results[0]["score"] == 0.95
        mock_embed_query.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.services.qdrant_service.search_vectors")
    @patch("app.utils.llm.embed_query")
    async def test_semantic_search_with_meeting_filter(self, mock_embed_query, mock_search_vectors):
        """Test semantic search with meeting filter"""
        mock_embed_query.return_value = [0.1, 0.2, 0.3]
        mock_search_vectors.return_value = [
            MagicMock(id="1", score=0.95, payload={"meeting_id": "m1"}, vector=[]),
        ]

        results = await semantic_search_with_filters(
            "test query",
            top_k=5,
            meeting_ids=["m1"],
        )

        assert len(results) == 1
        mock_search_vectors.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.services.qdrant_service.search_vectors")
    @patch("app.utils.llm.embed_query")
    async def test_semantic_search_with_project_filter(self, mock_embed_query, mock_search_vectors):
        """Test semantic search with project filter"""
        mock_embed_query.return_value = [0.1, 0.2, 0.3]
        mock_search_vectors.return_value = [
            MagicMock(id="1", score=0.95, payload={"project_id": "p1"}, vector=[]),
        ]

        results = await semantic_search_with_filters(
            "test query",
            top_k=5,
            project_ids=["p1"],
        )

        assert len(results) == 1

    @pytest.mark.asyncio
    @patch("app.services.qdrant_service.search_vectors")
    @patch("app.utils.llm.embed_query")
    async def test_semantic_search_with_file_filter(self, mock_embed_query, mock_search_vectors):
        """Test semantic search with file filter"""
        mock_embed_query.return_value = [0.1, 0.2, 0.3]
        mock_search_vectors.return_value = [
            MagicMock(id="1", score=0.95, payload={"file_id": "f1"}, vector=[]),
        ]

        results = await semantic_search_with_filters(
            "test query",
            top_k=5,
            file_ids=["f1"],
        )

        assert len(results) == 1

    @pytest.mark.asyncio
    @patch("app.services.qdrant_service.search_vectors")
    @patch("app.utils.llm.embed_query")
    async def test_semantic_search_with_multiple_filters(self, mock_embed_query, mock_search_vectors):
        """Test semantic search with multiple filters"""
        mock_embed_query.return_value = [0.1, 0.2, 0.3]
        mock_search_vectors.return_value = [
            MagicMock(id="1", score=0.95, payload={"project_id": "p1", "file_id": "f1"}, vector=[]),
        ]

        results = await semantic_search_with_filters(
            "test query",
            top_k=5,
            project_ids=["p1"],
            file_ids=["f1"],
        )

        assert len(results) == 1

    @pytest.mark.asyncio
    @patch("app.utils.llm.embed_query")
    async def test_semantic_search_embedding_fails(self, mock_embed_query):
        """Test semantic search when embedding fails"""
        mock_embed_query.return_value = None

        results = await semantic_search_with_filters("test query", top_k=5)

        assert results == []

    @pytest.mark.asyncio
    @patch("app.services.qdrant_service.search_vectors")
    async def test_semantic_search_with_provided_vector(self, mock_search_vectors):
        """Test semantic search with pre-computed vector"""
        mock_search_vectors.return_value = [
            MagicMock(id="1", score=0.95, payload={"text": "result1"}, vector=[]),
        ]

        query_vector = [0.1, 0.2, 0.3]
        results = await semantic_search_with_filters(
            "test query",
            top_k=5,
            query_vector=query_vector,
        )

        assert len(results) == 1


class TestProcessFile:
    """Tests for process_file function"""

    @pytest.mark.asyncio
    @patch("app.services.qdrant_service.chunk_text")
    @patch("app.services.qdrant_service.create_collection_if_not_exist")
    @patch("app.services.qdrant_service.upsert_vectors")
    @patch("app.utils.llm.embed_documents")
    @patch("app.services.qdrant_service._read_text_file")
    async def test_process_file_success(
        self,
        mock_read_file,
        mock_embed_docs,
        mock_upsert,
        mock_create_collection,
        mock_chunk_text,
        tmp_path,
    ):
        """Test processing a file successfully"""
        # Create a temporary file
        test_file = tmp_path / "test.txt"
        test_file.write_text("Test content for processing")

        mock_read_file.return_value = "Test content for processing"
        mock_chunk_text.return_value = ["chunk1", "chunk2"]
        mock_embed_docs.return_value = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        mock_upsert.return_value = True
        mock_create_collection.return_value = True

        result = await process_file(
            str(test_file),
            collection_name="test_collection",
            file_id="f1",
            project_id="p1",
        )

        assert result is True
        mock_create_collection.assert_called_once()
        mock_upsert.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_file_not_found(self):
        """Test processing non-existent file"""
        result = await process_file(
            "/nonexistent/file.txt",
            collection_name="test_collection",
            file_id="f1",
        )

        assert result is False

    @pytest.mark.asyncio
    @patch("app.services.qdrant_service._read_text_file")
    async def test_process_file_empty_content(self, mock_read_file, tmp_path):
        """Test processing file with empty content"""
        test_file = tmp_path / "empty.txt"
        test_file.write_text("")

        mock_read_file.return_value = ""

        result = await process_file(
            str(test_file),
            collection_name="test_collection",
            file_id="f1",
        )

        assert result is False

    @pytest.mark.asyncio
    @patch("app.services.qdrant_service.chunk_text")
    @patch("app.services.qdrant_service.create_collection_if_not_exist")
    @patch("app.services.qdrant_service.upsert_vectors")
    @patch("app.utils.llm.embed_documents")
    @patch("app.services.qdrant_service._read_text_file")
    async def test_process_file_with_metadata(
        self,
        mock_read_file,
        mock_embed_docs,
        mock_upsert,
        mock_create_collection,
        mock_chunk_text,
        tmp_path,
    ):
        """Test processing file with metadata"""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Test content")

        mock_read_file.return_value = "Test content"
        mock_chunk_text.return_value = ["chunk1"]
        mock_embed_docs.return_value = [[0.1, 0.2, 0.3]]
        mock_upsert.return_value = True
        mock_create_collection.return_value = True

        result = await process_file(
            str(test_file),
            collection_name="test_collection",
            file_id="f1",
            project_id="p1",
            meeting_id="m1",
            owner_user_id="u1",
            file_type="document",
        )

        assert result is True
        # Verify upsert was called with payloads containing metadata
        call_args = mock_upsert.call_args
        payloads = call_args[0][2]
        assert all("file_id" in p for p in payloads)
        assert all("project_id" in p for p in payloads)


class TestDeleteFileVectors:
    """Tests for delete_file_vectors function"""

    @pytest.mark.asyncio
    @patch("app.services.qdrant_service.get_qdrant_client")
    async def test_delete_file_vectors_success(self, mock_get_client):
        """Test deleting file vectors successfully"""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        result = await delete_file_vectors("f1", collection_name="test_collection")

        assert result is True
        mock_client.delete.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.services.qdrant_service.get_qdrant_client")
    async def test_delete_file_vectors_exception(self, mock_get_client):
        """Test deleting file vectors with exception"""
        mock_client = MagicMock()
        mock_client.delete.side_effect = Exception("Delete error")
        mock_get_client.return_value = mock_client

        result = await delete_file_vectors("f1", collection_name="test_collection")

        assert result is False


class TestDeleteTranscriptVectors:
    """Tests for delete_transcript_vectors function"""

    @pytest.mark.asyncio
    @patch("app.services.qdrant_service.get_qdrant_client")
    async def test_delete_transcript_vectors_success(self, mock_get_client):
        """Test deleting transcript vectors successfully"""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        result = await delete_transcript_vectors("t1", collection_name="test_collection")

        assert result is True
        mock_client.delete.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.services.qdrant_service.get_qdrant_client")
    async def test_delete_transcript_vectors_exception(self, mock_get_client):
        """Test deleting transcript vectors with exception"""
        mock_client = MagicMock()
        mock_client.delete.side_effect = Exception("Delete error")
        mock_get_client.return_value = mock_client

        result = await delete_transcript_vectors("t1", collection_name="test_collection")

        assert result is False


class TestUpdateFileVectorsMetadata:
    """Tests for update_file_vectors_metadata function"""

    @pytest.mark.asyncio
    @patch("app.services.qdrant_service.get_qdrant_client")
    async def test_update_file_vectors_metadata_success(self, mock_get_client):
        """Test updating file vectors metadata successfully"""
        mock_client = MagicMock()
        mock_point = MagicMock(id="1")
        mock_client.scroll.return_value = ([mock_point], None)
        mock_get_client.return_value = mock_client

        result = await update_file_vectors_metadata(
            "f1",
            project_id="p1",
            collection_name="test_collection",
        )

        assert result is True
        mock_client.set_payload.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.services.qdrant_service.get_qdrant_client")
    async def test_update_file_vectors_metadata_no_vectors(self, mock_get_client):
        """Test updating metadata when no vectors found"""
        mock_client = MagicMock()
        mock_client.scroll.return_value = ([], None)
        mock_get_client.return_value = mock_client

        result = await update_file_vectors_metadata(
            "f1",
            project_id="p1",
            collection_name="test_collection",
        )

        assert result is True
        mock_client.set_payload.assert_not_called()

    @pytest.mark.asyncio
    @patch("app.services.qdrant_service.get_qdrant_client")
    async def test_update_file_vectors_metadata_exception(self, mock_get_client):
        """Test updating metadata with exception"""
        mock_client = MagicMock()
        mock_client.scroll.side_effect = Exception("Scroll error")
        mock_get_client.return_value = mock_client

        result = await update_file_vectors_metadata(
            "f1",
            project_id="p1",
            collection_name="test_collection",
        )

        assert result is False


class TestReindexFile:
    """Tests for reindex_file function"""

    @pytest.mark.asyncio
    @patch("app.services.qdrant_service.chunk_text")
    @patch("app.services.qdrant_service.process_file")
    @patch("app.services.qdrant_service.delete_file_vectors")
    async def test_reindex_file_success(self, mock_delete, mock_process, mock_chunk_text, tmp_path):
        """Test reindexing file successfully"""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Test content")

        mock_delete.return_value = True
        mock_process.return_value = True
        mock_chunk_text.return_value = ["chunk1"]

        result = await reindex_file(
            str(test_file),
            file_id="f1",
            collection_name="test_collection",
        )

        assert result is True
        mock_delete.assert_called_once_with("f1", "test_collection")
        mock_process.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.services.qdrant_service.delete_file_vectors")
    async def test_reindex_file_not_found(self, mock_delete):
        """Test reindexing non-existent file"""
        mock_delete.return_value = True

        result = await reindex_file(
            "/nonexistent/file.txt",
            file_id="f1",
            collection_name="test_collection",
        )

        assert result is False


class TestQueryDocumentsByMeetingId:
    """Tests for query_documents_by_meeting_id function"""

    @pytest.mark.asyncio
    @patch("app.services.qdrant_service.get_qdrant_client")
    async def test_query_documents_by_meeting_id_success(self, mock_get_client):
        """Test querying documents by meeting ID"""
        mock_client = MagicMock()
        mock_point = MagicMock(id="1", payload={"meeting_id": "m1", "text": "content"})
        mock_client.scroll.return_value = ([mock_point], None)
        mock_get_client.return_value = mock_client

        results = await query_documents_by_meeting_id("m1", collection_name="test_collection", top_k=10)

        assert len(results) == 1
        assert results[0]["payload"]["meeting_id"] == "m1"

    @pytest.mark.asyncio
    @patch("app.services.qdrant_service.get_qdrant_client")
    async def test_query_documents_by_meeting_id_no_results(self, mock_get_client):
        """Test querying documents with no results"""
        mock_client = MagicMock()
        mock_client.scroll.return_value = ([], None)
        mock_get_client.return_value = mock_client

        results = await query_documents_by_meeting_id("m1", collection_name="test_collection", top_k=10)

        assert results == []

    @pytest.mark.asyncio
    @patch("app.services.qdrant_service.get_qdrant_client")
    async def test_query_documents_by_meeting_id_exception(self, mock_get_client):
        """Test querying documents with exception"""
        mock_client = MagicMock()
        mock_client.scroll.side_effect = Exception("Query error")
        mock_get_client.return_value = mock_client

        results = await query_documents_by_meeting_id("m1", collection_name="test_collection", top_k=10)

        assert results == []


class TestQueryDocumentsByProjectId:
    """Tests for query_documents_by_project_id function"""

    @pytest.mark.asyncio
    @patch("app.services.qdrant_service.get_qdrant_client")
    async def test_query_documents_by_project_id_success(self, mock_get_client):
        """Test querying documents by project ID"""
        mock_client = MagicMock()
        mock_point = MagicMock(id="1", payload={"project_id": "p1", "text": "content"})
        mock_client.scroll.return_value = ([mock_point], None)
        mock_get_client.return_value = mock_client

        results = await query_documents_by_project_id("p1", collection_name="test_collection", top_k=10)

        assert len(results) == 1
        assert results[0]["payload"]["project_id"] == "p1"

    @pytest.mark.asyncio
    @patch("app.services.qdrant_service.get_qdrant_client")
    async def test_query_documents_by_project_id_no_results(self, mock_get_client):
        """Test querying documents with no results"""
        mock_client = MagicMock()
        mock_client.scroll.return_value = ([], None)
        mock_get_client.return_value = mock_client

        results = await query_documents_by_project_id("p1", collection_name="test_collection", top_k=10)

        assert results == []

    @pytest.mark.asyncio
    @patch("app.services.qdrant_service.get_qdrant_client")
    async def test_query_documents_by_project_id_exception(self, mock_get_client):
        """Test querying documents with exception"""
        mock_client = MagicMock()
        mock_client.scroll.side_effect = Exception("Query error")
        mock_get_client.return_value = mock_client

        results = await query_documents_by_project_id("p1", collection_name="test_collection", top_k=10)

        assert results == []


class TestQueryDocumentsByFileId:
    """Tests for query_documents_by_file_id function"""

    @pytest.mark.asyncio
    @patch("app.services.qdrant_service.get_qdrant_client")
    async def test_query_documents_by_file_id_success(self, mock_get_client):
        """Test querying documents by file ID"""
        mock_client = MagicMock()
        mock_point = MagicMock(id="1", payload={"file_id": "f1", "text": "content"})
        mock_client.scroll.return_value = ([mock_point], None)
        mock_get_client.return_value = mock_client

        results = await query_documents_by_file_id("f1", collection_name="test_collection", top_k=10)

        assert len(results) == 1
        assert results[0]["payload"]["file_id"] == "f1"

    @pytest.mark.asyncio
    @patch("app.services.qdrant_service.get_qdrant_client")
    async def test_query_documents_by_file_id_no_results(self, mock_get_client):
        """Test querying documents with no results"""
        mock_client = MagicMock()
        mock_client.scroll.return_value = ([], None)
        mock_get_client.return_value = mock_client

        results = await query_documents_by_file_id("f1", collection_name="test_collection", top_k=10)

        assert results == []

    @pytest.mark.asyncio
    @patch("app.services.qdrant_service.get_qdrant_client")
    async def test_query_documents_by_file_id_exception(self, mock_get_client):
        """Test querying documents with exception"""
        mock_client = MagicMock()
        mock_client.scroll.side_effect = Exception("Query error")
        mock_get_client.return_value = mock_client

        results = await query_documents_by_file_id("f1", collection_name="test_collection", top_k=10)

        assert results == []
