import asyncio
import hashlib
import json
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from agno.models.message import Message
from celery import shared_task
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.jobs.celery_worker import celery_app
from app.models.chat import ChatMessage, ChatMessageType
from app.models.file import File
from app.models.meeting import AudioFile, Meeting
from app.schemas.notification import NotificationCreate
from app.services.audit_service import AuditLogService
from app.services.chat import perform_query_expansion_search
from app.services.notification import create_notifications_bulk, send_fcm_notification
from app.services.qdrant_service import reindex_file
from app.services.transcript import transcribe_audio_file
from app.utils.llm import (
    create_general_chat_agent,
    get_agno_postgres_db,
    optimize_contexts_with_llm,
)
from app.utils.redis import get_redis_client
from app.utils.task_progress import (
    publish_task_progress_sync,
    update_task_progress,
)

# Database setup for tasks
engine = create_engine(
    str(settings.SQLALCHEMY_DATABASE_URI),
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
# Attempt to establish Redis connection, but fall back to a no-op client in test
sync_redis_client = get_redis_client()


# --- Domain Event Processing (Audit) ---
@celery_app.task(bind=True, soft_time_limit=300, time_limit=600)
def process_domain_event(self, event_dict: dict) -> None:
    """Minimal Celery task to persist a domain event as an audit log.

    This task is intentionally light-weight and must not perform business logic.
    """
    import logging

    logger = logging.getLogger(__name__)

    try:
        service = AuditLogService()
        service.write_log(event_dict)
    except Exception as e:
        logger.error(f"Domain event task failed: {type(e).__name__}: {str(e)}")


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

        # Create notification for task completion
        notification_data = NotificationCreate(
            user_ids=[uuid.UUID(user_id)],
            type="task.file_indexing.completed",
            payload={
                "task_id": task_id,
                "file_id": file_id,
                "filename": file.filename,
                "task_type": "file_indexing",
                "status": "completed",
            },
            channel="in_app",
        )
        create_notifications_bulk(
            db,
            notification_data.user_ids,
            type=notification_data.type,
            payload=notification_data.payload,
            channel=notification_data.channel,
        )

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

        # Perform real audio transcription
        transcript = transcribe_audio_file(db, uuid.UUID(audio_file_id))
        if not transcript:
            raise Exception(f"Failed to transcribe audio file {audio_file_id}")

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

        # Create notifications and send FCM to meeting members
        create_notifications_bulk(
            db,
            target_user_ids,
            type="audio_processing_completed",
            payload={
                "audio_file_id": audio_file_id,
                "meeting_id": str(meeting_id),
                "processed_by": actor_user_id,
            },
        )
        send_fcm_notification(
            target_user_ids,
            "Audio Processing Completed",
            f"Audio processing has been completed for meeting: {meeting_id}",
            {
                "audio_file_id": audio_file_id,
                "meeting_id": str(meeting_id),
                "type": "audio_processing_completed",
            },
        )

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
def process_chat_message(
    self,  # noqa: ARG001
    conversation_id: str,
    user_message_id: str,
    content: str,
    user_id: str,
    query_results: Optional[List[dict]] = None,
) -> Dict[str, Any]:
    """
    Process chat message in background and broadcast response via SSE.

    This task handles AI processing and broadcasts the response via Redis for SSE clients.
    """

    print(f"[process_chat_message] Start processing: conversation_id={conversation_id}, user_message_id={user_message_id}, user_id={user_id}")
    # Create database session for this task
    db = SessionLocal()
    # Ensure user_id is always a plain string for downstream integrations (Agno expects str)
    user_id_str = str(user_id) if user_id is not None else ""

    try:
        print("[process_chat_message] Getting Agno Postgres DB instance...")
        # Get Agno DB for agent
        agno_db = get_agno_postgres_db()

        print("[process_chat_message] Creating general chat agent...")
        # Create chat agent
        agent = create_general_chat_agent(agno_db, conversation_id, user_id_str)

        print("[process_chat_message] Fetching conversation history...")
        # Fetch conversation history (using sync version for Celery task)
        history = fetch_conversation_history_sync(conversation_id)

        # Prepare retrieval contexts
        mention_docs: List[Dict[str, Any]] = list(query_results or [])
        combined_candidates: List[Dict[str, Any]] = mention_docs.copy()
        if mention_docs:
            print(f"[process_chat_message] Found {len(mention_docs)} mention-based documents for initial context.")
        else:
            print("[process_chat_message] No mention documents provided for context.")

        expansion_results: List[Dict[str, Any]] = []

        # Perform query expansion search for ALL chat messages
        print("[process_chat_message] Starting query expansion search...")
        try:
            # Get mentions from user message to pass as filters
            user_message = db.query(ChatMessage).filter(ChatMessage.id == user_message_id).first()
            mentions = user_message.mentions if user_message and user_message.mentions else []

            # Convert mentions to proper format if needed
            mention_objects = []
            if mentions:
                from app.schemas.chat import Mention

                for mention_data in mentions:
                    if isinstance(mention_data, dict):
                        mention_objects.append(Mention(**mention_data))
                    else:
                        mention_objects.append(mention_data)

            # Perform query expansion search
            expansion_results = asyncio.run(
                perform_query_expansion_search(
                    query=content,
                    mentions=mention_objects if mention_objects else None,
                    top_k=5,
                    num_expansions=3,
                )
            )

            if expansion_results:
                print(f"[process_chat_message] Found {len(expansion_results)} expansion-based results")
                combined_candidates.extend(expansion_results)
            else:
                print("[process_chat_message] No expansion results found")

        except Exception as expansion_error:
            print(f"[process_chat_message] Query expansion failed: {expansion_error}")
            expansion_results = []
            # Continue with mention-based results only

        # Deduplicate contexts by file_id + chunk_index (fallback to doc id)
        aggregated_contexts: Dict[str, Dict[str, Any]] = {}
        for source_doc in combined_candidates:
            if not isinstance(source_doc, dict):
                continue

            payload = source_doc.get("payload") or {}
            if not isinstance(payload, dict):
                payload = {}

            file_id = payload.get("file_id")
            chunk_index = payload.get("chunk_index")
            doc_id = source_doc.get("id")

            if file_id is not None and chunk_index is not None:
                dedupe_key = f"{file_id}:{chunk_index}"
            elif doc_id is not None:
                dedupe_key = str(doc_id)
            else:
                digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:12]
                dedupe_key = f"fallback:{digest}"

            score = float(source_doc.get("score", 0.0) or 0.0)
            normalized_doc = {
                "id": doc_id if doc_id is not None else dedupe_key,
                "score": score,
                "payload": dict(payload),
                "vector": source_doc.get("vector", []),
                "key": dedupe_key,
            }

            existing_doc = aggregated_contexts.get(dedupe_key)
            if existing_doc is None or score > existing_doc.get("score", 0.0):
                aggregated_contexts[dedupe_key] = normalized_doc

        combined_results: List[Dict[str, Any]] = sorted(
            aggregated_contexts.values(),
            key=lambda item: item["score"],
            reverse=True,
        )[:5]

        print(f"[process_chat_message] Aggregated {len(combined_results)} context documents after dedupe")

        # Optimization layer using LLM rerank
        optimized_contexts: List[Dict[str, Any]] = combined_results[:]
        if combined_results:
            context_map = {doc["key"]: doc for doc in combined_results}
            context_lines = []
            for doc in combined_results:
                snippet = (doc.get("payload", {}).get("text") or "")[:200].replace("\n", " ").strip()
                context_lines.append(f"{doc['key']} | score={doc.get('score', 0.0):.4f} | text={snippet}")
            context_block = "\n".join(context_lines) if context_lines else "Khong co."

            history_summary_parts = []
            for item in history[-5:]:
                role = getattr(item, "role", "user")
                snippet = (getattr(item, "content", "") or "")[:200].replace("\n", " ").strip()
                history_summary_parts.append(f"{role}: {snippet}")
            history_summary = "\n".join(history_summary_parts) if history_summary_parts else "Khong co."

            desired_count = 3

            try:
                optimizer_start = time.perf_counter()
                optimizer_response = asyncio.run(
                    optimize_contexts_with_llm(
                        query=content,
                        history=history_summary,
                        context_block=context_block,
                        desired_count=desired_count,
                    )
                )
                optimizer_duration = time.perf_counter() - optimizer_start
                print(f"[process_chat_message] Context optimizer latency: {optimizer_duration:.2f}s")

                selection_payload = None
                if optimizer_response:
                    if isinstance(optimizer_response, str):
                        try:
                            selection_payload = json.loads(optimizer_response)
                        except json.JSONDecodeError as parse_error:
                            print(f"[process_chat_message] Optimizer JSON parse failed: {parse_error}")
                    elif isinstance(optimizer_response, (dict, list)):
                        selection_payload = optimizer_response

                if isinstance(selection_payload, dict) and "selected" in selection_payload:
                    selection_items = selection_payload["selected"]
                elif isinstance(selection_payload, list):
                    selection_items = selection_payload
                else:
                    selection_items = []

                optimized_contexts = []
                for item in selection_items:
                    if not isinstance(item, dict):
                        continue
                    candidate_key = item.get("id") or item.get("key")
                    if not candidate_key:
                        continue
                    candidate_doc = context_map.get(candidate_key)
                    if candidate_doc and candidate_doc not in optimized_contexts:
                        optimized_contexts.append(candidate_doc)
                    if len(optimized_contexts) >= desired_count:
                        break

                if not optimized_contexts:
                    optimized_contexts = combined_results[:desired_count]

            except Exception as optimizer_error:
                print(f"[process_chat_message] Context optimization failed: {optimizer_error}")
                optimized_contexts = combined_results[:desired_count]
        else:
            optimized_contexts = []

        # Build enhanced content for agent prompt
        enhanced_content = content
        if optimized_contexts:
            enhanced_content += "\n\nThông tin bổ sung từ tìm kiếm mở rộng:\n"
            for idx, doc in enumerate(optimized_contexts[:3], start=1):
                snippet = (doc.get("payload", {}).get("text") or "Nội dung không có sẵn.").strip()
                enhanced_content += f"\nTai lieu {idx} (score={doc.get('score', 0.0):.2f}):\n{snippet}\n"
        else:
            print("[process_chat_message] No context selected; agent will answer from query only.")

        print("[process_chat_message] Running agent for AI response...")
        # Process message with AI agent
        response = agent.run(enhanced_content, history=history)

        ai_response_content = response.content
        print(f"[process_chat_message] AI response generated. Length: {len(ai_response_content)} characters.")

        # Create AI message in database
        print("[process_chat_message] Creating AI message in database...")
        ai_message = ChatMessage(
            conversation_id=conversation_id,
            message_type=ChatMessageType.agent,
            content=ai_response_content,
            user_id=user_id_str,
        )
        db.add(ai_message)
        db.commit()
        db.refresh(ai_message)
        print(f"[process_chat_message] AI message committed to DB with id: {ai_message.id}")

        # Broadcast message via Redis to SSE channel
        channel = f"conversation:{conversation_id}:messages"
        message_data = {
            "type": "chat_message",
            "conversation_id": conversation_id,
            "message": {
                "id": str(ai_message.id),
                "content": ai_response_content,
                "message_type": "agent",
                "created_at": ai_message.created_at.isoformat(),
            },
        }

        print(f"[process_chat_message] Broadcasting AI message to Redis channel: {channel}")
        # Use sync Redis client for broadcasting in Celery task
        sync_redis_client.publish(channel, json.dumps(message_data))

        # Create notification for task completion
        notification_data = NotificationCreate(
            user_ids=[uuid.UUID(user_id_str)],
            type="task.chat_processing.completed",
            payload={
                "conversation_id": conversation_id,
                "user_message_id": user_message_id,
                "ai_message_id": str(ai_message.id),
                "task_type": "chat_processing",
                "status": "completed",
            },
            channel="in_app",
        )
        create_notifications_bulk(
            db,
            notification_data.user_ids,
            type=notification_data.type,
            payload=notification_data.payload,
            channel=notification_data.channel,
        )

        print("[process_chat_message] Processing complete. Returning success response.")
        return {
            "status": "success",
            "conversation_id": conversation_id,
            "user_message_id": user_message_id,
            "ai_message_id": str(ai_message.id),
            "message": "AI response processed and broadcasted successfully",
        }

    except Exception as e:
        print(f"[process_chat_message] Exception occurred: {e}")
        # Create error message in database
        error_message = ChatMessage(
            conversation_id=conversation_id,
            message_type=ChatMessageType.agent,
            content="I apologize, but I encountered an error processing your message. Please try again.",
            user_id=user_id_str,
        )
        db.add(error_message)
        db.commit()
        print(f"[process_chat_message] Error message committed to DB with id: {error_message.id}")

        # Try to broadcast error message
        channel = f"conversation:{conversation_id}:messages"
        error_data = {
            "type": "chat_message",
            "conversation_id": conversation_id,
            "message": {
                "id": str(error_message.id),
                "content": error_message.content,
                "message_type": "agent",
                "created_at": error_message.created_at.isoformat(),
                "error": True,
            },
        }

        print(f"[process_chat_message] Broadcasting error message to Redis channel: {channel}")
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


@celery_app.task(soft_time_limit=60, time_limit=120)
def publish_notification_to_redis_task(user_ids: list, notification_type: str, payload: dict, channel: str):
    """
    Celery task to publish notifications to Redis for WebSocket real-time delivery.
    """
    import asyncio

    from app.utils.redis import publish_to_user_channel

    try:

        async def publish_all():
            """Helper async function to publish to all users."""
            success_count = 0
            for user_id in user_ids:
                message = {
                    "type": "notification",
                    "data": {
                        "notification_type": notification_type,
                        "payload": payload,
                        "channel": channel,
                        "timestamp": asyncio.get_event_loop().time(),
                    },
                }
                try:
                    success = await publish_to_user_channel(str(user_id), message)
                    if success:
                        success_count += 1
                except Exception as e:
                    print(f"Failed to publish to user {user_id}: {e}")

            return success_count

        # Run async publishing within worker's event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            success_count = loop.run_until_complete(publish_all())
            print(f"Published notifications to {success_count}/{len(user_ids)} users via Redis")
            return {"status": "success", "published": success_count, "total": len(user_ids)}
        finally:
            loop.close()

    except Exception as e:
        print(f"Error in publish_notification_to_redis_task: {e}")
        raise


@celery_app.task(soft_time_limit=120, time_limit=240)
def send_fcm_notification_background_task(
    user_ids: list,
    title: str,
    body: str,
    payload: dict,
    icon: str = None,
    badge: str = None,
    sound: str = None,
    ttl: int = None,
):
    """
    Celery task to send FCM push notifications in background.
    """
    try:
        send_fcm_notification(
            user_ids,
            title,
            body,
            payload,
            icon=icon,
            badge=badge,
            sound=sound,
            ttl=ttl,
        )
        print(f"FCM notifications sent successfully to {len(user_ids)} users")
        return {"status": "success", "users_count": len(user_ids)}
    except Exception as e:
        print(f"Error in send_fcm_notification_background_task: {e}")
        raise


@celery_app.task(bind=True, soft_time_limit=300, time_limit=600)
def process_meeting_analysis_task(
    self,
    transcript: str,
    meeting_id: str,
    user_id: str,
    custom_prompt: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Background task to analyze meeting transcript with concurrent extraction.
    
    Progress stages:
    - 0%: Started
    - 10%: Validating transcript
    - 30%: Extracting tasks (concurrent with note generation)
    - 60%: Generating meeting note (concurrent with task extraction)
    - 90%: Saving to database
    - 100%: Completed
    
    Args:
        transcript: Meeting transcript text
        meeting_id: Meeting UUID
        user_id: User UUID who triggered the analysis
        custom_prompt: Optional custom prompt for note generation
        
    Returns:
        Dictionary with status, meeting_id, analysis results
    """
    task_id = self.request.id or f"meeting_analysis_{meeting_id}_{int(time.time())}"

    print(f"\033[94m🚀 Starting meeting analysis task for meeting {meeting_id}\033[0m")

    try:
        # Step 1: Started (0%)
        update_task_progress(task_id, user_id, 0, "started", task_type="meeting_analysis")
        publish_task_progress_sync(
            user_id, 0, "started", "120s", "meeting_analysis", task_id
        )
        print(f"\033[93m📋 Task {task_id}: Analysis started for meeting {meeting_id}\033[0m")

        # Step 2: Validating transcript (10%)
        update_task_progress(
            task_id, user_id, 10, "validating", task_type="meeting_analysis"
        )
        publish_task_progress_sync(
            user_id, 10, "validating", "110s", "meeting_analysis", task_id
        )
        print(f"\033[95m🔍 Validating transcript for meeting {meeting_id}\033[0m")

        if not transcript or len(transcript.strip()) < 100:
            raise Exception(
                f"Transcript too short or empty: {len(transcript.strip()) if transcript else 0} characters"
            )

        print(
            f"\033[92m✅ Transcript validated: {len(transcript)} characters\033[0m"
        )

        # Step 3: Processing with concurrent extraction (30%)
        update_task_progress(
            task_id, user_id, 30, "processing", task_type="meeting_analysis"
        )
        publish_task_progress_sync(
            user_id, 30, "processing", "90s", "meeting_analysis", task_id
        )
        print("\033[96m🔄 Starting concurrent extraction (tasks + note)\033[0m")

        # Import and run MeetingAnalyzer
        from app.utils.meeting_agent import MeetingAnalyzer

        analyzer = MeetingAnalyzer()

        # Run async analysis in sync context
        analysis_result = asyncio.run(
            analyzer.complete(transcript=transcript, custom_prompt=custom_prompt)
        )

        print(
            f"\033[92m✅ Analysis completed - tasks: {len(analysis_result.get('task_items', []))}, note_length: {len(analysis_result.get('meeting_note', ''))}\033[0m"
        )

        # Step 4: Saving to database (90%)
        update_task_progress(
            task_id, user_id, 90, "saving", task_type="meeting_analysis"
        )
        publish_task_progress_sync(
            user_id, 90, "saving", "10s", "meeting_analysis", task_id
        )
        print(f"\033[93m💾 Saving analysis results for meeting {meeting_id}\033[0m")

        # Create database session
        db = SessionLocal()

        try:
            # Import the helper function
            from app.services.meeting_note import save_meeting_analysis_results
            
            # Save results using the service layer
            saved_results = save_meeting_analysis_results(
                db=db,
                meeting_id=uuid.UUID(meeting_id),
                user_id=uuid.UUID(user_id),
                meeting_note_content=analysis_result.get("meeting_note", ""),
                task_items=analysis_result.get("task_items", []),
            )

            print(
                f"\033[92m✅ Meeting {meeting_id} updated with analysis results\033[0m"
            )
            print(
                f"\033[92m✅ Saved {len(saved_results.get('task_items', []))} tasks to database\033[0m"
            )

        finally:
            db.close()

        # Step 5: Completed (100%)
        update_task_progress(
            task_id, user_id, 100, "completed", task_type="meeting_analysis"
        )
        publish_task_progress_sync(
            user_id, 100, "completed", "0s", "meeting_analysis", task_id
        )

        # Create notification for task completion
        notification_data = NotificationCreate(
            user_ids=[uuid.UUID(user_id)],
            type="task.meeting_analysis.completed",
            payload={
                "task_id": task_id,
                "meeting_id": meeting_id,
                "task_type": "meeting_analysis",
                "status": "completed",
                "tasks_count": len(analysis_result.get("task_items", [])),
                "note_length": len(analysis_result.get("meeting_note", "")),
            },
            channel="in_app",
        )

        db = SessionLocal()
        try:
            create_notifications_bulk(
                db,
                notification_data.user_ids,
                type=notification_data.type,
                payload=notification_data.payload,
                channel=notification_data.channel,
            )
        finally:
            db.close()

        print(
            f"\033[92m🎉 Meeting analysis completed successfully for {meeting_id}\033[0m"
        )

        return {
            "status": "success",
            "meeting_id": meeting_id,
            "task_id": task_id,
            "analysis": analysis_result,
            "message": "Meeting analysis completed successfully",
        }

    except Exception as exc:
        print(f"\033[91m💥 Meeting analysis failed for {meeting_id}: {exc}\033[0m")

        # Publish failure state
        update_task_progress(task_id, user_id, 0, "failed", task_type="meeting_analysis")
        publish_task_progress_sync(
            user_id, 0, "failed", "0s", "meeting_analysis", task_id
        )

        # Create failure notification
        db = SessionLocal()
        try:
            notification_data = NotificationCreate(
                user_ids=[uuid.UUID(user_id)],
                type="task.meeting_analysis.failed",
                payload={
                    "task_id": task_id,
                    "meeting_id": meeting_id,
                    "task_type": "meeting_analysis",
                    "status": "failed",
                    "error": str(exc),
                },
                channel="in_app",
            )
            create_notifications_bulk(
                db,
                notification_data.user_ids,
                type=notification_data.type,
                payload=notification_data.payload,
                channel=notification_data.channel,
            )
        finally:
            db.close()

        raise
