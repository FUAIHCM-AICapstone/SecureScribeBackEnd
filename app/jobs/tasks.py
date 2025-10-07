import asyncio
import json
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from agno.models.message import Message
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.jobs.celery_worker import celery_app
from app.models.chat import ChatMessage, ChatMessageType
from app.models.file import File
from app.models.meeting import AudioFile, Meeting, Transcript
from app.services.qdrant_service import reindex_file
from app.utils.llm import create_general_chat_agent, get_agno_postgres_db
from app.utils.redis import get_redis_client
from app.utils.task_progress import (
    publish_task_progress_sync,
    update_task_progress,
)

# Database setup for tasks
engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
sync_redis_client = get_redis_client()


def fetch_conversation_history_sync(conversation_id: str, limit: int = 10) -> List[Message]:
    """Synchronous version of fetch_conversation_history for use in Celery tasks."""
    from app.db import SessionLocal
    from app.models.chat import ChatMessage

    db = SessionLocal()
    try:
        messages = db.query(ChatMessage).filter(ChatMessage.conversation_id == conversation_id).order_by(ChatMessage.created_at.desc()).limit(limit).all()

        history = []
        for msg in reversed(messages):  # Chronological order
            role = "user" if msg.message_type == ChatMessageType.user else "assistant"
            history.append(Message(role=role, content=msg.content))
        return history
    finally:
        db.close()


async def _perform_async_indexing(
    file_id: str,
    filename: str,
    project_id: str | None,
    meeting_id: str | None,
    owner_user_id: str | None,
    file_type: str | None,
) -> bool:
    """Async helper function to perform file indexing"""
    try:
        import os
        import tempfile

        from app.utils.minio import get_minio_client

        minio_client = get_minio_client()
        file_content = minio_client.get_object(settings.MINIO_BUCKET_NAME, file_id)

        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{filename}") as temp_file:
            temp_file.write(file_content.data)
            temp_file_path = temp_file.name

        try:
            # Use qdrant_service to reindex the file (cleans up old vectors first)
            success = await reindex_file(
                file_path=temp_file_path,
                file_id=str(file_id),
                collection_name=settings.QDRANT_COLLECTION_NAME,
                project_id=project_id,
                meeting_id=meeting_id,
                owner_user_id=owner_user_id,
                file_type=file_type,
            )
            return success
        finally:
            # Clean up temp file
            os.unlink(temp_file_path)

    except Exception as e:
        print(f"\033[91m❌ Async indexing error: {e}\033[0m")
        return False


@celery_app.task(bind=True, soft_time_limit=300, time_limit=600)
def index_file_task(self, file_id: str, user_id: str) -> Dict[str, Any]:
    """Background task to index a file for search"""
    task_id = self.request.id or f"index_file_{file_id}_{int(time.time())}"

    print(f"\033[94m🚀 Starting file indexing task for file {file_id}\033[0m")

    try:
        # Step 1: Started
        update_task_progress(task_id, user_id, 0, "started", task_type="file_indexing")
        publish_task_progress_sync(user_id, 0, "started", "60s", "file_indexing", task_id)
        print(f"\033[93m📋 Task {task_id}: Indexing started for file {file_id}\033[0m")

        # Create database session
        db = SessionLocal()

        # Step 2: Validating file
        update_task_progress(task_id, user_id, 10, "validating", task_type="file_indexing")
        publish_task_progress_sync(user_id, 10, "validating", "55s", "file_indexing", task_id)
        print(f"\033[95m🔍 Validating file {file_id}\033[0m")

        # Get file info
        file = db.query(File).filter(File.id == uuid.UUID(file_id)).first()
        if not file:
            raise Exception(f"File {file_id} not found")

        print(f"\033[92m✅ File validated: {file.filename} ({file.mime_type})\033[0m")

        # Step 3: Extracting text
        update_task_progress(task_id, user_id, 25, "extracting_text", task_type="file_indexing")
        publish_task_progress_sync(user_id, 25, "extracting_text", "45s", "file_indexing", task_id)
        print(f"\033[96m📄 Extracting text from {file.filename}\033[0m")

        # Step 4: Chunking text
        update_task_progress(task_id, user_id, 40, "chunking_text", task_type="file_indexing")
        publish_task_progress_sync(user_id, 40, "chunking_text", "35s", "file_indexing", task_id)
        print("\033[94m✂️ Preparing to chunk text\033[0m")

        # Step 5: Generating embeddings
        update_task_progress(task_id, user_id, 60, "generating_embeddings", task_type="file_indexing")
        publish_task_progress_sync(user_id, 60, "generating_embeddings", "25s", "file_indexing", task_id)
        print("\033[95m🧠 Generating embeddings\033[0m")

        # Step 6: Storing vectors
        update_task_progress(task_id, user_id, 80, "storing_vectors", task_type="file_indexing")
        publish_task_progress_sync(user_id, 80, "storing_vectors", "15s", "file_indexing", task_id)
        print("\033[93m💾 Storing vectors in Qdrant\033[0m")

        # Step 7: Update database
        update_task_progress(task_id, user_id, 95, "updating_database", task_type="file_indexing")
        publish_task_progress_sync(user_id, 95, "updating_database", "5s", "file_indexing", task_id)

        # Perform the actual indexing
        print(f"\033[94m🚀 Starting actual indexing process for file {file_id}\033[0m")

        try:
            # Use asyncio.run to handle the async indexing
            success = asyncio.run(
                _perform_async_indexing(
                    file_id,
                    file.filename,
                    str(file.project_id) if file.project_id else None,
                    str(file.meeting_id) if file.meeting_id else None,
                    str(file.uploaded_by) if file.uploaded_by else None,
                    str(file.file_type) if file.file_type else None,
                )
            )

        except Exception as e:
            print(f"\033[91m❌ Error during indexing: {e}\033[0m")
            success = False

        if not success:
            raise Exception("Indexing failed")

        # Update database with indexing completion
        print(f"\033[93m💾 Updating database for file {file_id}\033[0m")
        file.qdrant_vector_id = str(file_id)  # Mark as indexed
        file.updated_at = datetime.utcnow()
        db.commit()
        print(f"\033[92m✅ Database updated: file {file_id} marked as indexed\033[0m")

        # Step 8: Completed
        update_task_progress(task_id, user_id, 100, "completed", task_type="file_indexing")
        publish_task_progress_sync(user_id, 100, "completed", "0s", "file_indexing", task_id)

        # Get filename before closing session
        filename = file.filename

        db.close()

        print(f"\033[92m🎉 File indexing completed successfully for {file_id}\033[0m")

        return {
            "status": "success",
            "file_id": file_id,
            "filename": filename,
            "message": "File indexed successfully",
        }

    except Exception as exc:
        print(f"\033[91m💥 File indexing failed for {file_id}: {exc}\033[0m")

        # Publish failure state
        update_task_progress(task_id, user_id, 0, "failed", task_type="file_indexing")
        publish_task_progress_sync(user_id, 0, "failed", "0s", "file_indexing", task_id)

        try:
            db.close()
        except Exception:
            pass

        raise


def _get_meeting_member_ids(db, meeting_id: uuid.UUID, include_creator: bool = True):
    members = []
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        return members
    if include_creator:
        members.append(meeting.created_by)

    from app.models.project import UserProject
    from app.utils.meeting import get_meeting_projects

    project_ids = get_meeting_projects(db, meeting_id)
    if project_ids:
        rows = db.query(UserProject.user_id).filter(UserProject.project_id.in_(project_ids)).all()
        members.extend([r[0] for r in rows])
    return list(set(members))


@celery_app.task(bind=True, soft_time_limit=300, time_limit=600)
def process_audio_task(self, audio_file_id: str, actor_user_id: str) -> Dict[str, Any]:
    task_id = self.request.id or f"process_audio_{audio_file_id}_{int(time.time())}"
    db = SessionLocal()
    try:
        audio = db.query(AudioFile).filter(AudioFile.id == uuid.UUID(audio_file_id)).first()
        if not audio:
            raise Exception(f"AudioFile {audio_file_id} not found")

        meeting_id = audio.meeting_id
        target_user_ids = _get_meeting_member_ids(db, meeting_id, include_creator=True)

        def _broadcast(progress: int, status: str, eta: str = ""):
            for uid in target_user_ids:
                publish_task_progress_sync(str(uid), progress, status, eta, "audio_asr", task_id)

        update_task_progress(task_id, actor_user_id, 0, "started", task_type="audio_asr")
        _broadcast(0, "started", "60s")

        update_task_progress(task_id, actor_user_id, 25, "processing", task_type="audio_asr")
        _broadcast(25, "processing", "45s")

        update_task_progress(task_id, actor_user_id, 75, "transcribing", task_type="audio_asr")
        _broadcast(75, "transcribing", "20s")

        now_iso = datetime.utcnow().isoformat() + "Z"
        mock_content = f"Mock transcript generated at {now_iso} for meeting {meeting_id}.\nThis is placeholder content for ASR processing of audio {audio_file_id}."

        transcript = db.query(Transcript).filter(Transcript.meeting_id == meeting_id).first()
        if not transcript:
            transcript = Transcript(meeting_id=meeting_id, content=mock_content)
            db.add(transcript)
        else:
            transcript.content = mock_content
        db.commit()
        db.refresh(transcript)

        try:
            from app.core.config import settings as _settings
            from app.services.qdrant_service import (
                chunk_text,
                create_collection_if_not_exist,
                upsert_vectors,
            )
            from app.utils.llm import embed_documents

            chunks = chunk_text(transcript.content or "")
            if chunks:
                vectors = asyncio.run(embed_documents(chunks))
                if vectors:
                    asyncio.run(create_collection_if_not_exist(_settings.QDRANT_COLLECTION_NAME, len(vectors[0])))
                payloads = [
                    {
                        "text": ch,
                        "chunk_index": i,
                        "meeting_id": str(meeting_id),
                        "transcript_id": str(transcript.id),
                        "total_chunks": len(chunks),
                    }
                    for i, ch in enumerate(chunks)
                ]
                asyncio.run(upsert_vectors(_settings.QDRANT_COLLECTION_NAME, vectors, payloads))
                transcript.qdrant_vector_id = str(transcript.id)
                db.commit()
        except Exception:
            pass

        update_task_progress(task_id, actor_user_id, 100, "completed", task_type="audio_asr")
        _broadcast(100, "completed", "0s")

        return {
            "status": "success",
            "audio_file_id": audio_file_id,
            "meeting_id": str(meeting_id),
        }
    except Exception:
        update_task_progress(task_id, actor_user_id, 0, "failed", task_type="audio_asr")
        try:
            audio = db.query(AudioFile).filter(AudioFile.id == uuid.UUID(audio_file_id)).first()
            if audio:
                for uid in _get_meeting_member_ids(db, audio.meeting_id, include_creator=True):
                    publish_task_progress_sync(str(uid), 0, "failed", "", "audio_asr", task_id)
        except Exception:
            pass
        raise
    finally:
        try:
            db.close()
        except Exception:
            pass


@celery_app.task(bind=True)
def process_chat_message(self, conversation_id: str, user_message_id: str, content: str, user_id: str, query_results: Optional[List[dict]] = None) -> Dict[str, Any]:
    """
    Process chat message in background and broadcast response via SSE.

    This task handles AI processing and broadcasts the response via Redis for SSE clients.
    """

    # Create database session for this task
    db = SessionLocal()

    try:
        # Get Agno DB for agent
        agno_db = get_agno_postgres_db()

        # Create chat agent
        agent = create_general_chat_agent(agno_db, conversation_id, user_id)

        # Fetch conversation history (using sync version for Celery task)
        history = fetch_conversation_history_sync(conversation_id)

        # Prepare enhanced content with meeting documents if available
        enhanced_content = content
        if query_results:
            meeting_context = "\n\nThông tin từ tài liệu cuộc họp được tìm thấy:\n"
            for i, doc in enumerate(query_results[:3]):  # Limit to 3 documents for context
                meeting_context += f"\nTài liệu {i + 1}:\n{doc.get('payload', {}).get('text', 'Nội dung không có sẵn')}\n"
            enhanced_content = content + meeting_context

        # Process message with AI agent
        response = agent.run(enhanced_content, history=history)

        ai_response_content = response.content

        # Create AI message in database
        ai_message = ChatMessage(conversation_id=conversation_id, message_type=ChatMessageType.agent, content=ai_response_content, user_id=user_id)
        db.add(ai_message)
        db.commit()
        db.refresh(ai_message)

        # Broadcast message via Redis to SSE channel
        channel = f"conversation:{conversation_id}:messages"
        message_data = {"type": "chat_message", "conversation_id": conversation_id, "message": {"id": str(ai_message.id), "content": ai_response_content, "message_type": "agent", "created_at": ai_message.created_at.isoformat()}}

        # Use sync Redis client for broadcasting in Celery task
        sync_redis_client.publish(channel, json.dumps(message_data))

        return {
            "status": "success",
            "conversation_id": conversation_id,
            "user_message_id": user_message_id,
            "ai_message_id": str(ai_message.id),
            "message": "AI response processed and broadcasted successfully",
        }

    except Exception as e:
        # Create error message in database
        error_message = ChatMessage(conversation_id=conversation_id, message_type=ChatMessageType.agent, content="I apologize, but I encountered an error processing your message. Please try again.", user_id=user_id)
        db.add(error_message)
        db.commit()

        # Try to broadcast error message
        channel = f"conversation:{conversation_id}:messages"
        error_data = {"type": "chat_message", "conversation_id": conversation_id, "message": {"id": str(error_message.id), "content": error_message.content, "message_type": "agent", "created_at": error_message.created_at.isoformat(), "error": True}}

        # Use sync Redis client for error broadcasting
        sync_redis_client.publish(channel, json.dumps(error_data))

        return {
            "status": "error",
            "conversation_id": conversation_id,
            "user_message_id": user_message_id,
            "error": str(e),
            "message": "AI processing failed",
        }

    finally:
        # Cleanup database session
        db.close()
