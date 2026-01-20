from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.crud.meeting_agenda import (
    crud_create_meeting_agenda,
    crud_delete_meeting_agenda,
    crud_get_meeting_agenda,
    crud_update_meeting_agenda,
)
from app.events.domain_events import BaseDomainEvent
from app.schemas.meeting_agenda import MeetingAgendaGenerateResponse
from app.services.event_manager import EventManager
from app.services.meeting import get_meeting
from app.services.qdrant_service import (
    query_documents_by_meeting_id,
    query_documents_by_project_id,
)
from app.utils.llm import _get_model
from app.utils.logging import logger
from app.utils.sliding_window import extract_important_notes_from_chunk


def get_meeting_agenda(db: Session, meeting_id: UUID, user_id: UUID) -> Optional[Any]:
    get_meeting(db, meeting_id, user_id, raise_404=True)
    return crud_get_meeting_agenda(db, meeting_id)


def create_meeting_agenda(db: Session, meeting_id: UUID, user_id: UUID, content: str) -> Optional[Any]:
    existing_agenda = crud_get_meeting_agenda(db, meeting_id)
    if existing_agenda:
        return update_meeting_agenda(db, meeting_id, user_id, content)
    get_meeting(db, meeting_id, user_id, raise_404=True)
    agenda = crud_create_meeting_agenda(db, meeting_id, content, user_id)
    EventManager.emit_domain_event(BaseDomainEvent(event_name="meeting_agenda.created", actor_user_id=user_id, target_type="meeting_agenda", target_id=meeting_id, metadata={"content_length": len(agenda.content) if agenda.content else 0}))
    return agenda


def update_meeting_agenda(db: Session, meeting_id: UUID, user_id: UUID, content: str) -> Optional[Any]:
    agenda = get_meeting_agenda(db, meeting_id, user_id)
    if not agenda:
        return None
    original_content = agenda.content
    agenda = crud_update_meeting_agenda(db, meeting_id, content, user_id)
    if original_content != agenda.content:
        EventManager.emit_domain_event(BaseDomainEvent(event_name="meeting_agenda.updated", actor_user_id=user_id, target_type="meeting_agenda", target_id=meeting_id, metadata={"diff": {"content": [original_content, agenda.content]}}))
    return agenda


def delete_meeting_agenda(db: Session, meeting_id: UUID, user_id: UUID) -> bool:
    agenda = get_meeting_agenda(db, meeting_id, user_id)
    if not agenda:
        return False
    if crud_delete_meeting_agenda(db, meeting_id):
        EventManager.emit_domain_event(BaseDomainEvent(event_name="meeting_agenda.deleted", actor_user_id=user_id, target_type="meeting_agenda", target_id=meeting_id, metadata={}))
        return True
    return False


def save_meeting_agenda_results(db: Session, meeting_id: UUID, user_id: UUID, agenda_content: str, token_usage: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Save meeting agenda results with token tracking and event emission.
    Handles both create and regenerate cases consistently.

    Args:
        db: Database session
        meeting_id: Meeting ID
        user_id: User ID
        agenda_content: Generated agenda content
        token_usage: Token usage dict from LLM

    Returns:
        Dictionary with agenda, content, and token_usage
    """
    existing_agenda = crud_get_meeting_agenda(db, meeting_id)
    is_regeneration = existing_agenda is not None
    token_usage = token_usage or {}

    if is_regeneration:
        # Update existing agenda
        agenda = crud_update_meeting_agenda(db, meeting_id, agenda_content, user_id)
        agenda.input_tokens = token_usage.get("input_tokens")
        agenda.output_tokens = token_usage.get("output_tokens")
        agenda.total_tokens = token_usage.get("total_tokens")
        db.commit()
        db.refresh(agenda)
        EventManager.emit_domain_event(
            BaseDomainEvent(
                event_name="meeting_agenda.regenerated",
                actor_user_id=user_id,
                target_type="meeting_agenda",
                target_id=meeting_id,
                metadata={
                    "content_length": len(agenda.content) if agenda.content else 0,
                    "regenerated": True,
                    "token_usage": token_usage,
                },
            )
        )
    else:
        # Create new agenda
        agenda = crud_create_meeting_agenda(db, meeting_id, agenda_content, user_id)
        agenda.input_tokens = token_usage.get("input_tokens")
        agenda.output_tokens = token_usage.get("output_tokens")
        agenda.total_tokens = token_usage.get("total_tokens")
        db.commit()
        db.refresh(agenda)
        EventManager.emit_domain_event(
            BaseDomainEvent(
                event_name="meeting_agenda.generated",
                actor_user_id=user_id,
                target_type="meeting_agenda",
                target_id=meeting_id,
                metadata={
                    "content_length": len(agenda.content) if agenda.content else 0,
                    "token_usage": token_usage,
                },
            )
        )

    return {"agenda": agenda, "content": agenda_content, "token_usage": token_usage}


async def generate_meeting_agenda_with_ai(
    db: Session,
    meeting_id: UUID,
    user_id: UUID,
    custom_prompt: Optional[str] = None,
    meeting_type_hint: Optional[str] = None,
) -> MeetingAgendaGenerateResponse:
    """
    Generate meeting agenda using AI based on indexed documents only.

    Flow:
    1. Verify user has access to meeting
    2. Query indexed documents from Qdrant by meeting_id
    3. Query indexed documents from Qdrant by project_id(s)
    4. Extract important notes from each document chunk
    5. Generate agenda from notes
    6. Save result to database with token tracking

    IMPORTANT: Document retrieval prioritization (for transcript-focused agendas):
    - If meeting has transcript: Use as PRIMARY context (80%)
    - Meeting files: SECONDARY context (15%)
    - Project files: REFERENCE context only (5%)
    - Note: Agenda generation extracts from indexed documents, not transcript directly.
      For transcript-focused agendas, the transcript should be indexed as a document.

    Args:
        db: Database session
        meeting_id: Meeting ID
        user_id: User ID
        custom_prompt: Custom prompt to override default agenda generation prompt
        meeting_type_hint: Type hint for meeting (business, technical, brainstorming, etc.)

    Returns:
        MeetingAgendaGenerateResponse with generated agenda and token usage
    """
    meeting = get_meeting(db, meeting_id, user_id, raise_404=True)

    # Log request parameters
    logger.info(f"[AGENDA GEN] Request for meeting {meeting_id}: meeting_type={meeting_type_hint}, custom_prompt={'Yes (len=' + str(len(custom_prompt)) + ')' if custom_prompt else 'No'}")

    try:
        # Step 1: Query documents from Qdrant by meeting_id
        logger.info(f"[AGENDA GEN] Starting document retrieval for meeting {meeting_id}")
        documents_data = await query_documents_by_meeting_id(str(meeting_id), top_k=10, db=db, user_id=str(user_id))

        # Extract text content from document results (Qdrant format: payload.text)
        documents = []
        document_metadata = []  # Store point_id for later updates
        if documents_data:
            logger.info(f"[AGENDA GEN] Found {len(documents_data)} documents from meeting {meeting_id}")
            for idx, doc in enumerate(documents_data, 1):
                content = None
                point_id = None
                existing_notes = None
                if isinstance(doc, dict):
                    payload = doc.get("payload") or {}
                    if isinstance(payload, dict):
                        content = payload.get("text")
                        existing_notes = payload.get("important_notes")
                    if not content:
                        content = doc.get("content")
                    point_id = doc.get("id")
                    logger.debug(f"[AGENDA GEN] Meeting doc {idx} structure: id={point_id}, score={doc.get('score'):.4f}, payload_keys={payload.keys() if isinstance(payload, dict) else 'N/A'}")
                elif isinstance(doc, str):
                    content = doc
                else:
                    payload = getattr(doc, "payload", None) or {}
                    if isinstance(payload, dict):
                        content = payload.get("text")
                        existing_notes = payload.get("important_notes")
                    if not content:
                        content = getattr(doc, "content", None)
                    point_id = getattr(doc, "id", None)
                    logger.debug(f"[AGENDA GEN] Meeting doc {idx} type={type(doc).__name__}, payload_keys={payload.keys() if isinstance(payload, dict) else 'N/A'}")

                if content:
                    preview = content[:150].replace("\n", " ") + ("..." if len(content) > 150 else "")
                    logger.debug(f"[AGENDA GEN] Meeting doc {idx} preview: {preview}")
                    logger.debug(f"[AGENDA GEN] Meeting doc {idx} FULL CONTENT:\n{content}")
                    documents.append(content)
                    document_metadata.append({"point_id": point_id, "existing_notes": existing_notes})
                else:
                    logger.warning(f"[AGENDA GEN] Meeting doc {idx} has no extractable text content")
        else:
            logger.warning(f"[AGENDA GEN] No documents found from meeting {meeting_id}")

        # Step 2: Query documents from projects that meeting belongs to
        try:
            if meeting.projects:
                logger.info(f"[AGENDA GEN] Meeting {meeting_id} belongs to {len(meeting.projects)} project(s)")
                for pm in meeting.projects:
                    project_id = pm.project_id
                    logger.info(f"[AGENDA GEN] Querying documents from project {project_id}")
                    project_docs = await query_documents_by_project_id(str(project_id), top_k=5, db=db, user_id=str(user_id))
                    if project_docs:
                        logger.info(f"[AGENDA GEN] Found {len(project_docs)} documents from project {project_id}")
                        for idx, doc in enumerate(project_docs, 1):
                            content = None
                            point_id = None
                            existing_notes = None
                            if isinstance(doc, dict):
                                payload = doc.get("payload") or {}
                                if isinstance(payload, dict):
                                    content = payload.get("text")
                                    existing_notes = payload.get("important_notes")
                                if not content:
                                    content = doc.get("content")
                                point_id = doc.get("id")
                                logger.debug(f"[AGENDA GEN] Project {project_id} doc {idx} structure: id={point_id}, score={doc.get('score'):.4f}, payload_keys={payload.keys() if isinstance(payload, dict) else 'N/A'}")
                            elif isinstance(doc, str):
                                content = doc
                            else:
                                payload = getattr(doc, "payload", None) or {}
                                if isinstance(payload, dict):
                                    content = payload.get("text")
                                    existing_notes = payload.get("important_notes")
                                if not content:
                                    content = getattr(doc, "content", None)
                                point_id = getattr(doc, "id", None)
                                logger.debug(f"[AGENDA GEN] Project {project_id} doc {idx} type={type(doc).__name__}, payload_keys={payload.keys() if isinstance(payload, dict) else 'N/A'}")

                            if content:
                                preview = content[:150].replace("\n", " ") + ("..." if len(content) > 150 else "")
                                logger.debug(f"[AGENDA GEN] Project {project_id} doc {idx} preview: {preview}")
                                logger.debug(f"[AGENDA GEN] Project {project_id} doc {idx} FULL CONTENT:\n{content}")
                                documents.append(content)
                                document_metadata.append({"point_id": point_id, "existing_notes": existing_notes})
                            else:
                                logger.warning(f"[AGENDA GEN] Project {project_id} doc {idx} has no extractable text content")
                    else:
                        logger.warning(f"[AGENDA GEN] No documents found from project {project_id}")
            else:
                logger.info(f"[AGENDA GEN] Meeting {meeting_id} has no associated projects")
        except Exception as e:
            logger.warning(f"[AGENDA GEN] Could not retrieve project documents for meeting {meeting_id}: {e}")

        # Step 3: Validate we have content (documents only)
        if not documents:
            logger.warning(f"No documents found for meeting {meeting_id}")
            from fastapi import HTTPException

            raise HTTPException(
                status_code=400,
                detail="No documents available to generate agenda. Please upload files.",
            )

        # Step 4: Build meeting metadata for context
        meeting_metadata = {
            "title": meeting.title or "Không có tiêu đề",
            "start_time": (meeting.start_time.strftime("%Y-%m-%d %H:%M") if meeting.start_time else "Chưa xác định"),
            "created_by_name": (meeting.created_by_user.name if meeting.created_by_user else "Không xác định"),
            "status": meeting.status,
            "projects": ([pm.project.name for pm in meeting.projects] if meeting.projects else []),
        }
        logger.debug(f"[AGENDA GEN] Meeting metadata: title={meeting_metadata['title']}, start_time={meeting_metadata['start_time']}, created_by={meeting_metadata['created_by_name']}, projects={meeting_metadata['projects']}")

        # Step 5: Extract important notes from each document chunk
        logger.info(f"[AGENDA GEN] Processing {len(documents)} document chunks for agenda generation")
        important_notes = []
        total_extraction_tokens = {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
        }

        for chunk_idx, chunk_text in enumerate(documents, 1):
            if not chunk_text or len(chunk_text.strip()) < 50:
                logger.debug(f"[AGENDA GEN] Skipping chunk {chunk_idx}: too short")
                continue

            logger.debug(f"[AGENDA GEN] Extracting notes from chunk {chunk_idx}/{len(documents)}")

            # Get metadata for this chunk
            meta = document_metadata[chunk_idx - 1] if chunk_idx - 1 < len(document_metadata) else {}
            point_id = meta.get("point_id")
            existing_notes = meta.get("existing_notes")

            # Pass existing_notes to check cache first
            chunk_notes, chunk_tokens = await extract_important_notes_from_chunk(chunk_text, existing_notes=existing_notes)

            if chunk_notes:
                important_notes.extend(chunk_notes)
                logger.info(f"[AGENDA GEN] Chunk {chunk_idx}: Extracted {len(chunk_notes)} notes (tokens: input={chunk_tokens.get('input_tokens', 0)}, output={chunk_tokens.get('output_tokens', 0)})")

                # Update vector payload if notes were newly extracted (not cached)
                if not existing_notes and point_id:
                    from app.core.config import settings as _settings
                    from app.utils.qdrant import update_vector_payload

                    update_vector_payload(
                        _settings.QDRANT_COLLECTION_NAME,
                        point_id,
                        {
                            "important_notes": chunk_notes,
                            "important_notes_count": len(chunk_notes),
                        },
                    )

            # Accumulate token usage from extraction
            total_extraction_tokens["input_tokens"] += chunk_tokens.get("input_tokens", 0)
            total_extraction_tokens["output_tokens"] += chunk_tokens.get("output_tokens", 0)
            total_extraction_tokens["total_tokens"] += chunk_tokens.get("total_tokens", 0)

        if not important_notes:
            logger.warning(f"No important notes extracted from documents for meeting {meeting_id}")
            from fastapi import HTTPException

            raise HTTPException(
                status_code=400,
                detail="No important information extracted from documents. Please try again.",
            )

        logger.info(f"[AGENDA GEN] Total {len(important_notes)} important notes extracted from all chunks")

        # Step 6: Call agenda generator with extracted important notes
        model = _get_model()

        from app.utils.meeting_agent.agenda_generator import generate_agenda_from_documents

        agenda_content, agenda_tokens = await generate_agenda_from_documents(
            documents=important_notes,
            model=model,
            meeting_type_hint=meeting_type_hint,
            custom_prompt=custom_prompt,
            meeting_metadata=meeting_metadata,
        )

        # Merge extraction and agenda generation tokens
        total_tokens = {
            "input_tokens": total_extraction_tokens.get("input_tokens", 0) + agenda_tokens.get("input_tokens", 0),
            "output_tokens": total_extraction_tokens.get("output_tokens", 0) + agenda_tokens.get("output_tokens", 0),
            "total_tokens": total_extraction_tokens.get("total_tokens", 0) + agenda_tokens.get("total_tokens", 0),
        }

        logger.info(f"[AGENDA GEN] Total token usage: extraction={total_extraction_tokens}, agenda={agenda_tokens}, total={total_tokens}")

        # Step 6: Save to database using helper function
        result = save_meeting_agenda_results(
            db=db,
            meeting_id=meeting_id,
            user_id=user_id,
            agenda_content=agenda_content,
            token_usage=total_tokens,
        )

        from app.schemas.meeting_agenda import MeetingAgendaResponse

        agenda = result["agenda"]
        agenda_response = MeetingAgendaResponse(
            id=str(agenda.id),
            content=agenda.content,
            last_edited_at=agenda.last_edited_at.isoformat() if agenda.last_edited_at else None,
            created_at=agenda.created_at.isoformat(),
            updated_at=agenda.updated_at.isoformat() if agenda.updated_at else None,
        )

        return MeetingAgendaGenerateResponse(
            agenda=agenda_response,
            content=agenda.content,
            token_usage=total_tokens if isinstance(total_tokens, dict) else None,
        )

    except Exception as e:
        logger.error(f"Error generating agenda for meeting {meeting_id}: {e}")
        from fastapi import HTTPException

        raise HTTPException(status_code=500, detail="Failed to generate agenda. Please try again.")
