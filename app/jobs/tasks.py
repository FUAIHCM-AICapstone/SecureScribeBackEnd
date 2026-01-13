import asyncio
import hashlib
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from agno.models.message import Message
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.jobs.celery_worker import celery_app
from app.models.chat import ChatMessage, ChatMessageType
from app.models.file import File
from app.models.meeting import AudioFile, Meeting, Transcript
from app.schemas.chat import Mention
from app.schemas.notification import NotificationCreate
from app.services import chat as chat_service
from app.services.audit_service import AuditLogService
from app.services.notification import create_notifications_bulk, send_fcm_notification
from app.services.qdrant_service import (
    chunk_text,
    delete_transcript_vectors,
    reindex_file,
)
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


async def update_meeting_vectors_with_project_id(meeting_id: str, project_id: str, collection_name: str) -> bool:
    """Update all vectors for a meeting with project_id.

    Args:
        meeting_id: Meeting UUID.
        project_id: Project UUID to assign.
        collection_name: Qdrant collection name.

    Returns:
        bool: True if successful, False on error.
    """
    try:
        import qdrant_client.models as qmodels

        from app.services.qdrant_service import get_qdrant_client

        client = get_qdrant_client()

        # Query all vectors for this meeting
        filter_condition = qmodels.Filter(must=[qmodels.FieldCondition(key="meeting_id", match=qmodels.MatchValue(value=meeting_id))])

        # Get all point IDs for this meeting
        all_points = []
        offset = None
        limit = 100

        while True:
            points, next_offset = client.scroll(
                collection_name=collection_name,
                scroll_filter=filter_condition,
                limit=limit,
                offset=offset,
                with_payload=False,
            )

            if not points:
                break

            all_points.extend([point.id for point in points])
            offset = next_offset

            if not offset:
                break

        if not all_points:
            print(f"\033[93m[QDRANT] No vectors found for meeting {meeting_id}\033[0m")
            return True

        # Update payload with project_id
        payload = {"project_id": project_id}

        client.set_payload(
            collection_name=collection_name,
            payload=payload,
            points=all_points,
            wait=True,
        )

        print(f"\033[92m[QDRANT] Updated {len(all_points)} vectors with project_id={project_id}\033[0m")
        return True

    except Exception as e:
        print(f"\033[91m[QDRANT] Failed to update meeting vectors: {str(e)}\033[0m")
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Update meeting vectors failed: {e}", exc_info=True)
        return False


# --- Domain Event Processing (Audit) ---
@celery_app.task(bind=True, soft_time_limit=300, time_limit=600)
def process_domain_event(self, event_dict: dict) -> None:  # noqa: ARG001
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
        file_content = minio_client.get_object(bucket_name=settings.MINIO_BUCKET_NAME, object_name=file_id)

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

    except Exception:
        return False


@celery_app.task(bind=True)
def index_file_task(self, file_id: str, user_id: str) -> Dict[str, Any]:
    """Background task to index a file for search"""
    task_id = self.request.id or f"index_file_{file_id}_{int(time.time())}"

    try:
        # Step 1: Started
        update_task_progress(task_id, user_id, 0, "started", task_type="file_indexing")
        publish_task_progress_sync(user_id, 0, "started", "60s", "file_indexing", task_id)

        # Create database session
        db = SessionLocal()

        # Step 2: Validating file
        update_task_progress(task_id, user_id, 10, "validating", task_type="file_indexing")
        publish_task_progress_sync(user_id, 10, "validating", "55s", "file_indexing", task_id)

        # Get file info
        file = db.query(File).filter(File.id == uuid.UUID(file_id)).first()
        if not file:
            raise Exception(f"File {file_id} not found")

        # Step 3: Extracting text
        update_task_progress(task_id, user_id, 25, "extracting_text", task_type="file_indexing")
        publish_task_progress_sync(user_id, 25, "extracting_text", "45s", "file_indexing", task_id)

        # Step 4: Chunking text
        update_task_progress(task_id, user_id, 40, "chunking_text", task_type="file_indexing")
        publish_task_progress_sync(user_id, 40, "chunking_text", "35s", "file_indexing", task_id)

        # Step 5: Generating embeddings
        update_task_progress(task_id, user_id, 60, "generating_embeddings", task_type="file_indexing")
        publish_task_progress_sync(user_id, 60, "generating_embeddings", "25s", "file_indexing", task_id)

        # Step 6: Storing vectors
        update_task_progress(task_id, user_id, 80, "storing_vectors", task_type="file_indexing")
        publish_task_progress_sync(user_id, 80, "storing_vectors", "15s", "file_indexing", task_id)

        # Step 7: Update database
        update_task_progress(task_id, user_id, 95, "updating_database", task_type="file_indexing")
        publish_task_progress_sync(user_id, 95, "updating_database", "5s", "file_indexing", task_id)

        # Perform the actual indexing

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

        except Exception:
            success = False

        if not success:
            raise Exception("Indexing failed")

        # Update database with indexing completion
        file.qdrant_vector_id = str(file_id)  # Mark as indexed
        file.updated_at = datetime.now(timezone.utc)
        db.commit()

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

        return {
            "status": "success",
            "file_id": file_id,
            "filename": filename,
            "message": "File indexed successfully",
        }

    except Exception:
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


@celery_app.task(bind=True)
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
        except Exception as qdrant_error:
            print(f"\033[93m[AUDIO_ASR] Qdrant indexing error (non-fatal): {str(qdrant_error)}\033[0m")
            # Non-fatal error - continue processing

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
def retry_webhook_processing_task(self, bot_id: str, meeting_url: str) -> Dict[str, Any]:  # noqa: ARG001
    """Retry failed webhook processing with exponential backoff"""
    import logging

    logger = logging.getLogger(__name__)

    try:
        logger.info(f"Retrying webhook processing for bot {bot_id}, meeting {meeting_url}")
        # Minimal implementation - just log the retry
        # In production, could implement exponential backoff and re-attempt
        return {
            "status": "retry_queued",
            "bot_id": bot_id,
            "meeting_url": meeting_url,
        }
    except Exception as e:
        logger.error(f"Retry task failed: {str(e)}")
        raise


@celery_app.task(bind=True)
def schedule_meeting_bot_task(self, meeting_id: str, user_id: str, bearer_token: str, meeting_url: str, bot_id: str, webhook_url: str = ""):  # noqa: ARG001
    """Schedule bot to join meeting at specified time"""

    import requests

    from app.core.config import settings

    try:
        # Use the provided bot_id instead of generating a new one
        payload = {
            "bearerToken": bearer_token,
            "url": meeting_url,
            "name": "Meeting Notetaker",
            "teamId": meeting_id,
            "timezone": "UTC",
            "userId": user_id,
            "botId": bot_id,
            "webhookUrl": webhook_url or settings.BOT_WEBHOOK_URL,
        }

        headers = {"Content-Type": "application/json"}
        bot_service_url = f"{settings.BOT_SERVICE_URL}/google/join"
        response = requests.post(bot_service_url, json=payload, headers=headers, timeout=30)

        if response.status_code == 202:
            return {"success": True, "bot_id": bot_id, "meeting_id": meeting_id}
        else:
            return {"success": False, "error": f"HTTP {response.status_code}", "meeting_id": meeting_id}

    except Exception as e:
        return {"success": False, "error": str(e), "meeting_id": meeting_id}


@celery_app.task(bind=True)
def process_chat_message(
    self,  # noqa: ARG001
    conversation_id: str,
    user_message_id: str,
    content: str,
    user_id: str,
    mentions: Optional[List[dict]] = None,
) -> Dict[str, Any]:
    """
    Process chat message in background and broadcast response via SSE.

    This task handles AI processing and broadcasts the response via Redis for SSE clients.
    """
    import logging

    logger = logging.getLogger(__name__)

    print("\033[94m[CHAT_PROCESS] Starting chat message processing task\033[0m")
    print(f"\033[94m[CHAT_PROCESS] Conversation ID: {conversation_id}, User Message ID: {user_message_id}, User ID: {user_id}\033[0m")

    # Create database session for this task
    db = SessionLocal()
    # Ensure user_id is always a plain string for downstream integrations (Agno expects str)
    user_id_str = str(user_id) if user_id is not None else ""
    print(f"\033[94m[CHAT_PROCESS] Database session created, User ID string: {user_id_str}\033[0m")

    try:
        print("\033[94m[CHAT_PROCESS] Getting Agno DB for agent\033[0m")
        # Get Agno DB for agent
        agno_db = get_agno_postgres_db()
        print("\033[92m[CHAT_PROCESS] Agno DB retrieved successfully\033[0m")

        print("\033[94m[CHAT_PROCESS] Creating chat agent\033[0m")
        # Create chat agent
        agent = create_general_chat_agent(agno_db, conversation_id, user_id_str)
        print("\033[92m[CHAT_PROCESS] Chat agent created successfully\033[0m")

        print("\033[94m[CHAT_PROCESS] Fetching conversation history\033[0m")
        # Fetch conversation history (using sync version for Celery task)
        history = fetch_conversation_history_sync(conversation_id)
        print(f"\033[92m[CHAT_PROCESS] Conversation history fetched: {len(history)} messages\033[0m")

        # Prepare retrieval contexts (already deduped/expanded at API layer)
        mention_models: List[Mention] = []
        if mentions:
            print(f"\033[94m[CHAT_PROCESS] Processing {len(mentions)} mentions\033[0m")
            for raw_mention in mentions:
                try:
                    if isinstance(raw_mention, Mention):
                        mention_models.append(raw_mention)
                    elif isinstance(raw_mention, dict):
                        mention_models.append(Mention(**raw_mention))
                    else:
                        mention_models.append(Mention.model_validate(raw_mention))
                except Exception as mention_parse_error:
                    print(f"\033[91m[CHAT_PROCESS] Failed to parse mention: {mention_parse_error}\033[0m")
            print(f"\033[92m[CHAT_PROCESS] Parsed {len(mention_models)} mention models\033[0m")

        combined_candidates: List[Dict[str, Any]] = []
        if mention_models:
            print("\033[94m[CHAT_PROCESS] Querying documents for mentions\033[0m")
            try:
                mention_candidates = asyncio.run(
                    chat_service.query_documents_for_mentions(
                        mention_models,
                        current_user_id=user_id_str or None,
                        db=db,
                        content=content,
                        include_query_expansion=False,
                    )
                )
                if mention_candidates:
                    combined_candidates.extend(mention_candidates)
                    print(f"\033[92m[CHAT_PROCESS] Found {len(mention_candidates)} mention candidates\033[0m")
            except Exception as mention_error:
                print(f"\033[91m[CHAT_PROCESS] Failed to query documents for mentions: {mention_error}\033[0m")

        expansion_candidates: List[Dict[str, Any]] = []
        normalized_content = (content or "").strip()
        if normalized_content:
            print("\033[94m[CHAT_PROCESS] Performing query expansion search\033[0m")
            try:
                expansion_candidates = asyncio.run(
                    chat_service.perform_query_expansion_search(
                        normalized_content,
                        mentions=mention_models or None,
                        top_k=5,
                        num_expansions=3,
                    )
                )
                if expansion_candidates:
                    combined_candidates.extend(expansion_candidates)
                    print(f"\033[92m[CHAT_PROCESS] Found {len(expansion_candidates)} expansion candidates\033[0m")
            except Exception as expansion_error:
                print(f"\033[91m[CHAT_PROCESS] Failed to perform expansion search: {expansion_error}\033[0m")
        else:
            print("\033[93m[CHAT_PROCESS] No content provided for expansion search\033[0m")

        print(f"\033[94m[CHAT_PROCESS] Total combined candidates: {len(combined_candidates)}\033[0m")

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

        print(f"\033[92m[CHAT_PROCESS] Deduplicated to {len(combined_results)} top results\033[0m")

        # Optimization layer using LLM rerank
        optimized_contexts: List[Dict[str, Any]] = combined_results[:]
        if combined_results:
            print("\033[94m[CHAT_PROCESS] Optimizing contexts with LLM rerank\033[0m")
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
                optimizer_response = asyncio.run(
                    optimize_contexts_with_llm(
                        query=content,
                        history=history_summary,
                        context_block=context_block,
                        desired_count=desired_count,
                    )
                )

                selection_payload = None
                if optimizer_response:
                    if isinstance(optimizer_response, str):
                        try:
                            selection_payload = json.loads(optimizer_response)
                        except json.JSONDecodeError:
                            selection_payload = None
                    elif isinstance(optimizer_response, dict | list):
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

                print(f"\033[92m[CHAT_PROCESS] Optimized to {len(optimized_contexts)} contexts\033[0m")

            except Exception as opt_error:
                print(f"\033[91m[CHAT_PROCESS] Context optimization failed: {opt_error}\033[0m")
                optimized_contexts = combined_results[:desired_count]
        else:
            print("\033[93m[CHAT_PROCESS] No combined results for optimization\033[0m")
            optimized_contexts = []

        # Build enhanced content for agent prompt
        enhanced_content = content
        if optimized_contexts:
            enhanced_content += "\n\nThông tin bổ sung từ tìm kiếm mở rộng:\n"
            for idx, doc in enumerate(optimized_contexts[:3], start=1):
                snippet = (doc.get("payload", {}).get("text") or "Nội dung không có sẵn.").strip()
                enhanced_content += f"\nTai lieu {idx} (score={doc.get('score', 0.0):.2f}):\n{snippet}\n"
            print(f"\033[92m[CHAT_PROCESS] Enhanced content built with {len(optimized_contexts)} contexts\033[0m")
        else:
            print("\033[93m[CHAT_PROCESS] No optimized contexts available for enhancement\033[0m")

        # Process message with AI agent
        print("\033[94m[CHAT_PROCESS] Processing message with AI agent\033[0m")
        print("=== Enhanced Content for Agent ===")
        print(enhanced_content)
        print("==================================")
        response = agent.run(enhanced_content, history=history)
        ai_response_content = response.content
        print(f"\033[92m[CHAT_PROCESS] AI response generated: {len(ai_response_content)} characters\033[0m")

        # Create AI message in database
        print("\033[94m[CHAT_PROCESS] Creating AI message in database\033[0m")
        ai_message = ChatMessage(
            conversation_id=conversation_id,
            message_type=ChatMessageType.agent,
            content=ai_response_content,
            user_id=user_id_str,
        )
        db.add(ai_message)
        db.commit()
        db.refresh(ai_message)
        print(f"\033[92m[CHAT_PROCESS] AI message created with ID: {ai_message.id}\033[0m")

        # Broadcast message via Redis to SSE channel
        print("\033[94m[CHAT_PROCESS] Broadcasting message via Redis\033[0m")
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

        # Use sync Redis client for broadcasting in Celery task
        sync_redis_client.publish(channel, json.dumps(message_data))
        print(f"\033[92m[CHAT_PROCESS] Message broadcasted to channel: {channel}\033[0m")

        # Create notification for task completion
        print("\033[94m[CHAT_PROCESS] Creating completion notification\033[0m")
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
        print("\033[92m[CHAT_PROCESS] Completion notification created\033[0m")

        print("\033[92m[CHAT_PROCESS] Chat message processing completed successfully\033[0m")
        return {
            "status": "success",
            "conversation_id": conversation_id,
            "user_message_id": user_message_id,
            "ai_message_id": str(ai_message.id),
            "message": "AI response processed and broadcasted successfully",
        }

    except Exception as e:
        print(f"\033[91m[CHAT_PROCESS] Exception occurred: {str(e)}\033[0m")
        logger.exception("Chat processing task failed")

        # Create error message in database
        print("\033[94m[CHAT_PROCESS] Creating error message in database\033[0m")
        error_message = ChatMessage(
            conversation_id=conversation_id,
            message_type=ChatMessageType.agent,
            content="I apologize, but I encountered an error processing your message. Please try again.",
            user_id=user_id_str,
        )
        db.add(error_message)
        db.commit()

        # Try to broadcast error message
        print("\033[94m[CHAT_PROCESS] Broadcasting error message\033[0m")
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

        # Use sync Redis client for error broadcasting
        sync_redis_client.publish(channel, json.dumps(error_data))
        print(f"\033[92m[CHAT_PROCESS] Error message broadcasted to channel: {channel}\033[0m")

        print("\033[91m[CHAT_PROCESS] Chat message processing failed\033[0m")
        return {
            "status": "error",
            "conversation_id": conversation_id,
            "user_message_id": user_message_id,
            "error": str(e),
            "message": "AI processing failed",
        }

    finally:
        # Cleanup database session
        print("\033[94m[CHAT_PROCESS] Cleaning up database session\033[0m")
        db.close()
        print("\033[92m[CHAT_PROCESS] Database session closed\033[0m")


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
                    print(f"Failed to publish notification to user {user_id}: {e}")

            return success_count

        try:
            asyncio.get_running_loop()
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as executor:
                executor.submit(asyncio.run, publish_all())
        except RuntimeError:
            asyncio.run(publish_all())

    except Exception:
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
        return {"status": "success", "users_count": len(user_ids)}
    except Exception:
        raise


@celery_app.task(soft_time_limit=60, time_limit=120)
def send_bot_status_notification_task(bot_id: str, status: str, error: Optional[str] = None):
    """
    Celery task to send bot status notification via WebSocket and FCM.
    Called asynchronously from sync context to avoid event loop issues.
    """
    import logging

    from app.services.bot_notification import send_bot_status_notification

    logger = logging.getLogger(__name__)

    try:
        db = SessionLocal()
        try:
            # Convert string bot_id to UUID
            bot_uuid = uuid.UUID(bot_id)

            # Run the async notification function
            import asyncio

            try:
                asyncio.get_running_loop()
                # If there's a running loop, use it with a thread executor
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    executor.submit(asyncio.run, send_bot_status_notification(db, bot_uuid, status, error))
            except RuntimeError:
                # No running loop, create a new one
                asyncio.run(send_bot_status_notification(db, bot_uuid, status, error))

            logger.info(f"Bot status notification sent: bot_id={bot_id}, status={status}")
            return {"status": "success", "bot_id": bot_id, "notification_status": status}

        finally:
            db.close()

    except Exception as e:
        logger.exception(f"Failed to send bot status notification: {e}")
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
    - 95%: Indexing meeting note to Qdrant
    - 97%: Updating project_id for existing vectors
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

    try:
        # Step 1: Started (0%)
        update_task_progress(task_id, user_id, 0, "started", task_type="meeting_analysis")
        publish_task_progress_sync(user_id, 0, "started", "120s", "meeting_analysis", task_id)

        # Step 2: Validating transcript (10%)
        update_task_progress(task_id, user_id, 10, "validating", task_type="meeting_analysis")
        publish_task_progress_sync(user_id, 10, "validating", "110s", "meeting_analysis", task_id)

        if not transcript or len(transcript.strip()) < 100:
            raise Exception(f"Transcript too short or empty: {len(transcript.strip()) if transcript else 0} characters")
        # query for meeting start time from database
        db = SessionLocal()
        try:
            meeting_obj = db.query(Meeting).filter(Meeting.id == uuid.UUID(meeting_id)).first()
            if meeting_obj and meeting_obj.start_time:
                meeting_start_time = meeting_obj.start_time.isoformat()
                meeting_title = meeting_obj.title or "Untitled Meeting"
                # Prepend meeting start time to transcript for context
                transcript = f"Title:{meeting_title}\nMeeting Start Time: {meeting_start_time}\n\n{transcript}"
        finally:
            db.close()

        # Step 3: Processing with concurrent extraction (30%)
        update_task_progress(task_id, user_id, 30, "processing", task_type="meeting_analysis")
        publish_task_progress_sync(user_id, 30, "processing", "90s", "meeting_analysis", task_id)

        # Import and run MeetingAnalyzer
        from app.utils.meeting_agent import MeetingAnalyzer

        analyzer = MeetingAnalyzer()

        # Run async analysis in sync context
        analysis_result = asyncio.run(analyzer.complete(transcript=transcript, custom_prompt=custom_prompt))

        # Step 4: Saving to database (90%)
        update_task_progress(task_id, user_id, 90, "saving", task_type="meeting_analysis")
        publish_task_progress_sync(user_id, 90, "saving", "10s", "meeting_analysis", task_id)

        # Create database session
        db = SessionLocal()

        try:
            # Import the helper function
            from app.services.meeting_note import save_meeting_analysis_results

            # Save results using the service layer
            save_meeting_analysis_results(
                db=db,
                meeting_id=uuid.UUID(meeting_id),
                user_id=uuid.UUID(user_id),
                meeting_note_content=analysis_result.get("meeting_note", ""),
                task_items=analysis_result.get("task_items", []),
            )

            # Step 4.5: Indexing meeting note to Qdrant (95%)
            update_task_progress(task_id, user_id, 95, "indexing_note", task_type="meeting_analysis")
            publish_task_progress_sync(user_id, 95, "indexing_note", "5s", "meeting_analysis", task_id)

            meeting_note_content = analysis_result.get("meeting_note", "")
            if meeting_note_content and len(meeting_note_content.strip()) > 0:
                try:
                    from app.core.config import settings as _settings
                    from app.services.qdrant_service import (
                        chunk_text,
                        create_collection_if_not_exist,
                        upsert_vectors,
                    )
                    from app.utils.llm import embed_documents

                    print(f"\033[94m[MEETING_ANALYSIS] Indexing meeting note ({len(meeting_note_content)} chars)\033[0m")

                    chunks = chunk_text(meeting_note_content)
                    if not chunks:
                        print("\033[93m[MEETING_ANALYSIS] No chunks generated from meeting note\033[0m")
                    else:
                        print(f"\033[94m[MEETING_ANALYSIS] Generated {len(chunks)} chunks\033[0m")
                        vectors = asyncio.run(embed_documents(chunks))
                        if not vectors:
                            print("\033[93m[MEETING_ANALYSIS] Failed to generate embeddings for chunks\033[0m")
                        else:
                            print(f"\033[94m[MEETING_ANALYSIS] Generated {len(vectors)} embeddings\033[0m")
                            asyncio.run(create_collection_if_not_exist(_settings.QDRANT_COLLECTION_NAME, len(vectors[0])))

                            payloads = [
                                {
                                    "text": ch,
                                    "chunk_index": i,
                                    "meeting_id": meeting_id,
                                    "note_type": "meeting_note",
                                    "total_chunks": len(chunks),
                                }
                                for i, ch in enumerate(chunks)
                            ]
                            success = asyncio.run(upsert_vectors(_settings.QDRANT_COLLECTION_NAME, vectors, payloads))
                            if success:
                                print("\033[92m[MEETING_ANALYSIS] Successfully indexed meeting note\033[0m")
                            else:
                                print("\033[93m[MEETING_ANALYSIS] Upsert vectors returned False\033[0m")

                except Exception as index_error:
                    import logging

                    logger = logging.getLogger(__name__)
                    error_msg = f"Meeting note indexing error: {type(index_error).__name__}: {str(index_error)}"
                    print(f"\033[93m[MEETING_ANALYSIS] {error_msg}\033[0m")
                    logger.warning(error_msg, exc_info=True)
            else:
                print("\033[93m[MEETING_ANALYSIS] No meeting note content to index\033[0m")

            # Step 4.6: Update project_id for existing vectors (97%)
            update_task_progress(task_id, user_id, 97, "updating_vectors", task_type="meeting_analysis")
            publish_task_progress_sync(user_id, 97, "updating_vectors", "3s", "meeting_analysis", task_id)

            try:
                # Get meeting's project_id from database
                meeting_obj = db.query(Meeting).filter(Meeting.id == uuid.UUID(meeting_id)).first()
                project_ids = []
                if meeting_obj and hasattr(meeting_obj, "projects") and meeting_obj.projects:
                    project_ids = [str(project_meeting.project_id) for project_meeting in meeting_obj.projects if project_meeting.project]

                asyncio.run(update_meeting_vectors_with_project_id(meeting_id, project_ids[0], _settings.QDRANT_COLLECTION_NAME))

            except Exception as update_vector_error:
                print(f"Failed to update meeting vectors with project_id: {update_vector_error}")

        finally:
            db.close()

        # Step 5: Completed (100%)
        update_task_progress(task_id, user_id, 100, "completed", task_type="meeting_analysis")
        publish_task_progress_sync(user_id, 100, "completed", "0s", "meeting_analysis", task_id)

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

        return {
            "status": "success",
            "meeting_id": meeting_id,
            "task_id": task_id,
            "analysis": analysis_result,
            "message": "Meeting analysis completed successfully",
        }

    except Exception as exc:
        # Publish failure state
        update_task_progress(task_id, user_id, 0, "failed", task_type="meeting_analysis")
        publish_task_progress_sync(user_id, 0, "failed", "0s", "meeting_analysis", task_id)

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


@celery_app.task(bind=True, soft_time_limit=300, time_limit=600)
def reindex_transcript_task(self, transcript_id: str, user_id: str) -> Dict[str, Any]:
    """
    Background task to reindex a transcript for search.

    Progress stages:
    - 0%: Started
    - 10%: Validating transcript
    - 25%: Deleting old vectors
    - 40%: Chunking text
    - 60%: Generating embeddings
    - 80%: Storing vectors
    - 95%: Updating database
    - 100%: Completed

    Args:
        transcript_id: Transcript UUID
        user_id: User UUID who triggered the reindex

    Returns:
        Dictionary with status, transcript_id, meeting_id
    """
    task_id = self.request.id or f"reindex_transcript_{transcript_id}_{int(time.time())}"

    try:
        # Step 1: Started (0%)
        update_task_progress(task_id, user_id, 0, "started", task_type="transcript_reindex")
        publish_task_progress_sync(user_id, 0, "started", "60s", "transcript_reindex", task_id)

        # Step 2: Validating transcript (10%)
        update_task_progress(task_id, user_id, 10, "validating", task_type="transcript_reindex")
        publish_task_progress_sync(user_id, 10, "validating", "55s", "transcript_reindex", task_id)

        db = SessionLocal()

        try:
            # Get transcript
            transcript = db.query(Transcript).filter(Transcript.id == uuid.UUID(transcript_id)).first()
            if not transcript:
                raise Exception(f"Transcript {transcript_id} not found")

            # Get meeting and validate access
            meeting = db.query(Meeting).filter(Meeting.id == transcript.meeting_id).first()
            if not meeting:
                raise Exception(f"Meeting {transcript.meeting_id} not found for transcript")

            if not transcript.content or len(transcript.content.strip()) < 10:
                raise Exception(f"Transcript content too short or empty: {len(transcript.content.strip()) if transcript.content else 0} characters")

            # Step 3: Deleting old vectors (25%)
            update_task_progress(task_id, user_id, 25, "deleting_old_vectors", task_type="transcript_reindex")
            publish_task_progress_sync(user_id, 25, "deleting_old_vectors", "45s", "transcript_reindex", task_id)

            # Delete old vectors using async function
            asyncio.run(delete_transcript_vectors(transcript_id, settings.QDRANT_COLLECTION_NAME))

            # Step 4: Chunking text (40%)
            update_task_progress(task_id, user_id, 40, "chunking_text", task_type="transcript_reindex")
            publish_task_progress_sync(user_id, 40, "chunking_text", "35s", "transcript_reindex", task_id)

            chunks = chunk_text(transcript.content)
            if not chunks:
                raise Exception("No chunks generated from transcript content")

            # Step 5: Generating embeddings (60%)
            update_task_progress(task_id, user_id, 60, "generating_embeddings", task_type="transcript_reindex")
            publish_task_progress_sync(user_id, 60, "generating_embeddings", "25s", "transcript_reindex", task_id)

            from app.core.config import settings as _settings
            from app.services.qdrant_service import (
                create_collection_if_not_exist,
                upsert_vectors,
            )
            from app.utils.llm import embed_documents

            vectors = asyncio.run(embed_documents(chunks))
            if not vectors:
                raise Exception("Failed to generate embeddings")

            # Step 6: Storing vectors (80%)
            update_task_progress(task_id, user_id, 80, "storing_vectors", task_type="transcript_reindex")
            publish_task_progress_sync(user_id, 80, "storing_vectors", "15s", "transcript_reindex", task_id)

            # Ensure collection exists
            asyncio.run(create_collection_if_not_exist(_settings.QDRANT_COLLECTION_NAME, len(vectors[0])))

            # Get project_id(s) from meeting
            project_ids = []
            primary_project_id = None
            if hasattr(meeting, "projects") and meeting.projects:
                project_ids = [str(project_meeting.project_id) for project_meeting in meeting.projects if project_meeting.project]
                primary_project_id = project_ids[0] if project_ids else None

            # Prepare payloads
            payloads = [
                {
                    "text": chunk,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "meeting_id": str(transcript.meeting_id),
                    "transcript_id": transcript_id,
                    "project_id": primary_project_id,
                    "note_type": "transcript",
                    "is_global": bool(not primary_project_id),
                }
                for i, chunk in enumerate(chunks)
            ]

            # Upsert vectors
            asyncio.run(upsert_vectors(_settings.QDRANT_COLLECTION_NAME, vectors, payloads))

            # Step 7: Updating database (95%)
            update_task_progress(task_id, user_id, 95, "updating_database", task_type="transcript_reindex")
            publish_task_progress_sync(user_id, 95, "updating_database", "5s", "transcript_reindex", task_id)

            # Update transcript
            transcript.qdrant_vector_id = transcript_id
            transcript.updated_at = datetime.now(timezone.utc)
            db.commit()

            # Step 8: Completed (100%)
            update_task_progress(task_id, user_id, 100, "completed", task_type="transcript_reindex")
            publish_task_progress_sync(user_id, 100, "completed", "0s", "transcript_reindex", task_id)

            # Create notification
            notification_data = NotificationCreate(
                user_ids=[uuid.UUID(user_id)],
                type="task.transcript_reindex.completed",
                payload={
                    "task_id": task_id,
                    "transcript_id": transcript_id,
                    "meeting_id": str(transcript.meeting_id),
                    "task_type": "transcript_reindex",
                    "status": "completed",
                    "chunks": len(chunks),
                    "vectors": len(vectors),
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

            return {
                "status": "success",
                "transcript_id": transcript_id,
                "meeting_id": str(transcript.meeting_id),
                "task_id": task_id,
                "chunks": len(chunks),
                "vectors": len(vectors),
                "message": "Transcript reindexed successfully",
            }

        finally:
            db.close()

    except Exception as exc:
        # Publish failure state
        update_task_progress(task_id, user_id, 0, "failed", task_type="transcript_reindex")
        publish_task_progress_sync(user_id, 0, "failed", "0s", "transcript_reindex", task_id)

        # Create failure notification
        db = SessionLocal()
        try:
            notification_data = NotificationCreate(
                user_ids=[uuid.UUID(user_id)],
                type="task.transcript_reindex.failed",
                payload={
                    "task_id": task_id,
                    "transcript_id": transcript_id,
                    "task_type": "transcript_reindex",
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
