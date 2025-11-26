"""Unit tests for Celery tasks"""

import uuid
from unittest.mock import AsyncMock, Mock, patch

import pytest
from faker import Faker
from sqlalchemy.orm import Session

from app.jobs.tasks import (
    fetch_conversation_history_sync,
    index_file_task,
    process_audio_task,
    process_chat_message,
    process_domain_event,
    process_meeting_analysis_task,
    publish_notification_to_redis_task,
    reindex_transcript_task,
    retry_webhook_processing_task,
    schedule_meeting_bot_task,
    send_fcm_notification_background_task,
    update_meeting_vectors_with_project_id,
)
from tests.factories import (
    AudioFileFactory,
    ConversationFactory,
    FileFactory,
    MeetingFactory,
    TranscriptFactory,
    UserFactory,
)

fake = Faker()


class TestProcessDomainEvent:
    """Tests for process_domain_event task"""

    def test_process_domain_event_success(self):
        """Test processing domain event successfully"""
        from app.services.audit_service import AuditLogService

        event_dict = {"event_name": "test.event", "actor_user_id": str(uuid.uuid4()), "target_type": "test", "target_id": str(uuid.uuid4()), "metadata": {"test": "data"}}

        with patch.object(AuditLogService, "write_log") as mock_write:
            process_domain_event(event_dict)
            mock_write.assert_called_once_with(event_dict)

    def test_process_domain_event_failure(self):
        """Test handling failure in domain event processing"""
        from app.services.audit_service import AuditLogService

        event_dict = {"event_name": "test.event"}

        with patch.object(AuditLogService, "write_log", side_effect=Exception("Test error")):
            # Should not raise exception, just log it
            process_domain_event(event_dict)


class TestFetchConversationHistorySync:
    """Tests for fetch_conversation_history_sync function"""

    def test_fetch_conversation_history_sync_success(self, db_session: Session):
        """Test fetching conversation history synchronously"""
        from app.models.chat import ChatMessage, ChatMessageType, Conversation

        user = UserFactory.create(db_session)
        conversation = ConversationFactory.create(db_session, user=user, title="Test Conversation")

        # Create test messages
        messages = []
        for i in range(3):
            msg = ChatMessage(conversation_id=conversation.id, message_type=ChatMessageType.user if i % 2 == 0 else ChatMessageType.agent, content=f"Message {i}", user_id=str(user.id))
            db_session.add(msg)
            messages.append(msg)
        db_session.commit()

        result = fetch_conversation_history_sync(str(conversation.id))

        assert len(result) == 3
        # Should be in chronological order (oldest first)
        assert result[0].content == "Message 0"  # Oldest first
        assert result[1].content == "Message 1"
        assert result[2].content == "Message 2"  # Most recent last

    def test_fetch_conversation_history_sync_empty(self, db_session: Session):
        """Test fetching history for conversation with no messages"""
        conversation_id = str(uuid.uuid4())
        result = fetch_conversation_history_sync(conversation_id)
        assert result == []


class TestIndexFileTask:
    """Tests for index_file_task Celery task"""

    @patch("app.jobs.tasks.update_task_progress")
    @patch("app.jobs.tasks.publish_task_progress_sync")
    @patch("app.jobs.tasks._perform_async_indexing")
    def test_index_file_task_success(self, mock_perform_indexing, mock_publish, mock_update_progress, db_session: Session):
        """Test successful file indexing task"""
        user = UserFactory.create(db_session)
        file_obj = FileFactory.create(db_session, uploaded_by=user)
        db_session.commit()

        mock_perform_indexing.return_value = True

        result = index_file_task(str(file_obj.id), str(user.id))

        assert result["status"] == "success"
        assert result["file_id"] == str(file_obj.id)
        assert "message" in result

        # Verify progress updates were called
        assert mock_update_progress.call_count >= 5  # Multiple progress updates
        assert mock_publish.call_count >= 5

    @patch("app.jobs.tasks.update_task_progress")
    @patch("app.jobs.tasks.publish_task_progress_sync")
    def test_index_file_task_file_not_found(self, mock_publish, mock_update_progress, db_session: Session):
        """Test indexing task when file doesn't exist"""
        user = UserFactory.create(db_session)
        fake_file_id = str(uuid.uuid4())

        with pytest.raises(Exception, match="File .* not found"):
            index_file_task(fake_file_id, str(user.id))


class TestProcessAudioTask:
    """Tests for process_audio_task Celery task"""

    @patch("app.jobs.tasks.update_task_progress")
    @patch("app.jobs.tasks.publish_task_progress_sync")
    @patch("app.jobs.tasks.transcribe_audio_file")
    @patch("app.services.qdrant_service.chunk_text")
    @patch("app.utils.llm.embed_documents")
    @patch("app.services.qdrant_service.create_collection_if_not_exist")
    @patch("app.services.qdrant_service.upsert_vectors")
    def test_process_audio_task_success(self, mock_upsert, mock_create_collection, mock_embed, mock_chunk, mock_transcribe, mock_publish, mock_update_progress, db_session: Session):
        """Test successful audio processing task"""
        user = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, created_by=user)
        audio_file = AudioFileFactory.create(db_session, meeting=meeting, uploaded_by=user)
        db_session.commit()

        # Mock transcription result
        mock_transcript = Mock()
        mock_transcript.id = uuid.uuid4()
        mock_transcript.content = "Test transcription"
        mock_transcribe.return_value = mock_transcript

        # Mock chunking and embedding
        mock_chunk.return_value = ["Chunk 1", "Chunk 2"]
        mock_embed.return_value = [[0.1, 0.2], [0.3, 0.4]]

        result = process_audio_task(str(audio_file.id), str(user.id))

        assert result["status"] == "success"
        assert result["audio_file_id"] == str(audio_file.id)
        assert result["meeting_id"] == str(meeting.id)

    @patch("app.jobs.tasks.update_task_progress")
    @patch("app.jobs.tasks.publish_task_progress_sync")
    def test_process_audio_task_audio_not_found(self, mock_publish, mock_update_progress, db_session: Session):
        """Test audio processing when audio file doesn't exist"""
        user = UserFactory.create(db_session)
        fake_audio_id = str(uuid.uuid4())

        with pytest.raises(Exception, match="AudioFile .* not found"):
            process_audio_task(fake_audio_id, str(user.id))


class TestProcessChatMessage:
    """Tests for process_chat_message Celery task"""

    @patch("app.jobs.tasks.get_agno_postgres_db")
    @patch("app.jobs.tasks.create_general_chat_agent")
    @patch("app.jobs.tasks.fetch_conversation_history_sync")
    @patch("app.jobs.tasks.chat_service.query_documents_for_mentions")
    @patch("app.jobs.tasks.chat_service.perform_query_expansion_search")
    @patch("app.jobs.tasks.optimize_contexts_with_llm")
    @patch("app.jobs.tasks.SessionLocal")
    def test_process_chat_message_success(self, mock_session_local, mock_optimize, mock_expansion_search, mock_mentions_query, mock_fetch_history, mock_create_agent, mock_get_db):
        """Test successful chat message processing"""
        # Mock database session
        mock_session = Mock()
        mock_session_local.return_value = mock_session

        # Mock agent
        mock_agent = Mock()
        mock_agent.run.return_value = Mock(content="AI response")
        mock_create_agent.return_value = mock_agent

        # Mock conversation history
        mock_fetch_history.return_value = []

        # Mock document queries
        mock_mentions_query.return_value = []
        mock_expansion_search.return_value = []

        # Mock LLM optimization
        mock_optimize.return_value = {"selected": []}

        # Mock chat message creation
        mock_ai_message = Mock()
        mock_ai_message.id = uuid.uuid4()
        mock_session.add.return_value = None
        mock_session.refresh.return_value = None

        conversation_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())

        result = process_chat_message(conversation_id=conversation_id, user_message_id=str(uuid.uuid4()), content="Test message", user_id=user_id, mentions=[])

        assert result["status"] == "success"
        assert result["conversation_id"] == conversation_id
        assert "ai_message_id" in result

    @patch("app.jobs.tasks.SessionLocal")
    def test_process_chat_message_exception_handling(self, mock_session_local):
        """Test exception handling in chat message processing"""
        mock_session = Mock()
        mock_session_local.return_value = mock_session

        # Force an exception early in the process
        with patch("app.jobs.tasks.get_agno_postgres_db", side_effect=Exception("Test error")):
            result = process_chat_message(conversation_id=str(uuid.uuid4()), user_message_id=str(uuid.uuid4()), content="Test message", user_id=str(uuid.uuid4()), mentions=[])

            assert result["status"] == "error"
            assert "error" in result


class TestScheduleMeetingBotTask:
    """Tests for schedule_meeting_bot_task"""

    @patch("requests.post")
    def test_schedule_meeting_bot_success(self, mock_post):
        """Test successful bot scheduling"""
        mock_response = Mock()
        mock_response.status_code = 202
        mock_response.json.return_value = {"success": True}
        mock_post.return_value = mock_response

        result = schedule_meeting_bot_task(meeting_id="test_meeting", user_id="test_user", bearer_token="test_token", meeting_url="https://meet.test.com", webhook_url="https://webhook.test.com")

        assert result["success"] is True
        assert "bot_id" in result

    @patch("requests.post")
    def test_schedule_meeting_bot_failure(self, mock_post):
        """Test bot scheduling failure"""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_post.return_value = mock_response

        result = schedule_meeting_bot_task(meeting_id="test_meeting", user_id="test_user", bearer_token="test_token", meeting_url="https://meet.test.com")

        assert result["success"] is False
        assert "error" in result


class TestProcessMeetingAnalysisTask:
    """Tests for process_meeting_analysis_task"""

    @patch("app.jobs.tasks.update_task_progress")
    @patch("app.jobs.tasks.publish_task_progress_sync")
    @patch("app.utils.meeting_agent.MeetingAnalyzer")
    @patch("app.services.meeting_note.save_meeting_analysis_results")
    @patch("app.services.qdrant_service.chunk_text")
    @patch("app.utils.llm.embed_documents")
    @patch("app.services.qdrant_service.create_collection_if_not_exist")
    @patch("app.services.qdrant_service.upsert_vectors")
    @patch("app.services.qdrant_service.delete_transcript_vectors")
    def test_process_meeting_analysis_success(self, mock_delete_vectors, mock_upsert, mock_create_collection, mock_embed, mock_chunk, mock_save_results, mock_analyzer_class, mock_publish, mock_update_progress, db_session: Session):
        """Test successful meeting analysis task"""
        user = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, created_by=user)
        db_session.commit()

        # Mock analyzer
        mock_analyzer = Mock()
        mock_analyzer.complete = AsyncMock(return_value={"meeting_note": "Test meeting note", "task_items": [{"title": "Test task"}]})
        mock_analyzer_class.return_value = mock_analyzer

        # Mock save results
        mock_save_results.return_value = {"task_items": [{"id": str(uuid.uuid4())}]}

        # Mock Qdrant operations
        mock_chunk.return_value = ["Chunk 1"]
        mock_embed.return_value = [[0.1, 0.2]]

        result = process_meeting_analysis_task("This is a test transcript that is long enough to pass validation. It needs to be at least 100 characters to work properly with the meeting analysis task.", str(meeting.id), str(user.id))

        assert result["status"] == "success"
        assert result["meeting_id"] == str(meeting.id)
        assert "analysis" in result


class TestReindexTranscriptTask:
    """Tests for reindex_transcript_task"""

    @patch("app.jobs.tasks.update_task_progress")
    @patch("app.jobs.tasks.publish_task_progress_sync")
    @patch("app.services.qdrant_service.delete_transcript_vectors")
    @patch("app.services.qdrant_service.chunk_text")
    @patch("app.utils.llm.embed_documents")
    @patch("app.services.qdrant_service.create_collection_if_not_exist")
    @patch("app.services.qdrant_service.upsert_vectors")
    def test_reindex_transcript_success(self, mock_upsert, mock_create_collection, mock_embed, mock_chunk, mock_delete_vectors, mock_publish, mock_update_progress, db_session: Session):
        """Test successful transcript reindexing"""
        user = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, created_by=user)
        transcript = TranscriptFactory.create(db_session, meeting=meeting, content="Test content")
        db_session.commit()

        # Mock operations
        mock_chunk.return_value = ["Chunk 1", "Chunk 2"]
        mock_embed.return_value = [[0.1, 0.2], [0.3, 0.4]]

        result = reindex_transcript_task(str(transcript.id), str(user.id))

        assert result["status"] == "success"
        assert result["transcript_id"] == str(transcript.id)
        assert "chunks" in result
        assert "vectors" in result


class TestUpdateMeetingVectorsWithProjectId:
    """Tests for update_meeting_vectors_with_project_id"""

    @pytest.mark.asyncio
    async def test_update_vectors_success(self):
        """Test successful vector update with project_id"""
        with patch("app.services.qdrant_service.get_qdrant_client") as mock_get_client:
            mock_client = Mock()
            mock_get_client.return_value = mock_client

            # Mock scroll operation
            mock_client.scroll.return_value = ([Mock(id="vector_1"), Mock(id="vector_2")], None)

            meeting_id = str(uuid.uuid4())
            project_id = str(uuid.uuid4())

            result = await update_meeting_vectors_with_project_id(meeting_id, project_id, "test_collection")

            assert result is True
            mock_client.set_payload.assert_called_once()
            args = mock_client.set_payload.call_args
            assert args[1]["payload"] == {"project_id": project_id}
            assert len(args[1]["points"]) == 2

    @pytest.mark.asyncio
    async def test_update_vectors_no_vectors_found(self):
        """Test when no vectors are found for meeting"""
        with patch("app.services.qdrant_service.get_qdrant_client") as mock_get_client:
            mock_client = Mock()
            mock_get_client.return_value = mock_client

            # Mock empty scroll result
            mock_client.scroll.return_value = ([], None)

            meeting_id = str(uuid.uuid4())
            project_id = str(uuid.uuid4())

            result = await update_meeting_vectors_with_project_id(meeting_id, project_id, "test_collection")

            assert result is True
            mock_client.set_payload.assert_not_called()


class TestPublishNotificationToRedisTask:
    """Tests for publish_notification_to_redis_task"""

    @patch("app.utils.redis.publish_to_user_channel")
    def test_publish_notification_success(self, mock_publish):
        """Test successful notification publishing"""
        mock_publish.return_value = True

        user_ids = [str(uuid.uuid4()), str(uuid.uuid4())]
        result = publish_notification_to_redis_task(user_ids=user_ids, notification_type="test.notification", payload={"test": "data"}, channel="test_channel")

        assert result["status"] == "success"
        assert result["published"] == 2
        assert result["total"] == 2

        # Verify publish was called for each user
        assert mock_publish.call_count == 2


class TestSendFcmNotificationBackgroundTask:
    """Tests for send_fcm_notification_background_task"""

    @patch("app.services.notification.send_fcm_notification")
    def test_send_fcm_success(self, mock_send_fcm):
        """Test successful FCM notification sending"""
        user_ids = [str(uuid.uuid4()), str(uuid.uuid4())]

        result = send_fcm_notification_background_task(user_ids=user_ids, title="Test Title", body="Test Body", payload={"test": "data"})

        assert result["status"] == "success"
        assert result["users_count"] == 2
        mock_send_fcm.assert_called_once()


class TestRetryWebhookProcessingTask:
    """Tests for retry_webhook_processing_task"""

    def test_retry_webhook_processing(self):
        """Test webhook retry processing"""
        result = retry_webhook_processing_task(bot_id="test_bot", meeting_url="https://meet.test.com")

        assert result["status"] == "retry_queued"
        assert result["bot_id"] == "test_bot"
        assert result["meeting_url"] == "https://meet.test.com"
