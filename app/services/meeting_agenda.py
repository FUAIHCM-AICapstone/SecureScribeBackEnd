from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.crud.meeting_agenda import crud_create_meeting_agenda, crud_delete_meeting_agenda, crud_get_meeting_agenda, crud_update_meeting_agenda
from app.events.domain_events import BaseDomainEvent
from app.schemas.meeting_agenda import MeetingAgendaGenerateResponse
from app.services.event_manager import EventManager
from app.services.meeting import get_meeting
from app.services.qdrant_service import query_documents_by_meeting_id, query_documents_by_project_id
from app.services.transcript import get_transcript_by_meeting
from app.utils.llm import _get_model
from app.utils.logging import logger
from app.utils.meeting_agent.agenda_generator import generate_agenda_from_documents


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
        agenda.input_tokens = token_usage.get("prompt_tokens")
        agenda.output_tokens = token_usage.get("completion_tokens")
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
        agenda.input_tokens = token_usage.get("prompt_tokens")
        agenda.output_tokens = token_usage.get("completion_tokens")
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


def generate_meeting_agenda_with_ai(db: Session, meeting_id: UUID, user_id: UUID, custom_prompt: Optional[str] = None, meeting_type_hint: Optional[str] = None) -> MeetingAgendaGenerateResponse:
    """
    Generate meeting agenda using AI based on indexed documents only.

    Flow:
    1. Verify user has access to meeting
    2. Query indexed documents from Qdrant by meeting_id
    3. Query indexed documents from Qdrant by project_id(s)
    4. Call agenda generator with documents
    5. Save result to database with token tracking
    
    Note: Only uses documents from indexed files, not transcript or meeting notes.
    
    Args:
        db: Database session
        meeting_id: Meeting ID
        user_id: User ID
        custom_prompt: Custom prompt to override default agenda generation prompt
        meeting_type_hint: Type hint for meeting (business, technical, brainstorming, etc.)
    
    Returns:
        MeetingAgendaGenerateResponse with generated agenda and token usage
    """
    import asyncio

    meeting = get_meeting(db, meeting_id, user_id, raise_404=True)
    
    # Log request parameters
    logger.info(f"[AGENDA GEN] Request for meeting {meeting_id}: meeting_type={meeting_type_hint}, custom_prompt={'Yes (len=' + str(len(custom_prompt)) + ')' if custom_prompt else 'No'}")

    try:
        # Step 1: Query documents from Qdrant by meeting_id
        logger.info(f"[AGENDA GEN] Starting document retrieval for meeting {meeting_id}")
        documents_data = asyncio.run(query_documents_by_meeting_id(str(meeting_id), top_k=10, db=db, user_id=str(user_id)))

        # Extract text content from document results (Qdrant format: payload.text)
        documents = []
        if documents_data:
            logger.info(f"[AGENDA GEN] Found {len(documents_data)} documents from meeting {meeting_id}")
            for idx, doc in enumerate(documents_data, 1):
                content = None
                if isinstance(doc, dict):
                    payload = doc.get("payload") or {}
                    if isinstance(payload, dict):
                        content = payload.get("text")
                    if not content:
                        content = doc.get("content")
                    logger.debug(f"[AGENDA GEN] Meeting doc {idx} structure: id={doc.get('id')}, score={doc.get('score'):.4f}, payload_keys={payload.keys() if isinstance(payload, dict) else 'N/A'}")
                elif isinstance(doc, str):
                    content = doc
                else:
                    payload = getattr(doc, "payload", None) or {}
                    if isinstance(payload, dict):
                        content = payload.get("text")
                    if not content:
                        content = getattr(doc, "content", None)
                    logger.debug(f"[AGENDA GEN] Meeting doc {idx} type={type(doc).__name__}, payload_keys={payload.keys() if isinstance(payload, dict) else 'N/A'}")
                
                if content:
                    preview = content[:150].replace("\n", " ") + ("..." if len(content) > 150 else "")
                    logger.debug(f"[AGENDA GEN] Meeting doc {idx} preview: {preview}")
                    logger.debug(f"[AGENDA GEN] Meeting doc {idx} FULL CONTENT:\n{content}")
                    documents.append(content)
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
                    project_docs = asyncio.run(query_documents_by_project_id(str(project_id), top_k=5, db=db, user_id=str(user_id)))
                    if project_docs:
                        logger.info(f"[AGENDA GEN] Found {len(project_docs)} documents from project {project_id}")
                        for idx, doc in enumerate(project_docs, 1):
                            content = None
                            if isinstance(doc, dict):
                                payload = doc.get("payload") or {}
                                if isinstance(payload, dict):
                                    content = payload.get("text")
                                if not content:
                                    content = doc.get("content")
                                logger.debug(f"[AGENDA GEN] Project {project_id} doc {idx} structure: id={doc.get('id')}, score={doc.get('score'):.4f}, payload_keys={payload.keys() if isinstance(payload, dict) else 'N/A'}")
                            elif isinstance(doc, str):
                                content = doc
                            else:
                                payload = getattr(doc, "payload", None) or {}
                                if isinstance(payload, dict):
                                    content = payload.get("text")
                                if not content:
                                    content = getattr(doc, "content", None)
                                logger.debug(f"[AGENDA GEN] Project {project_id} doc {idx} type={type(doc).__name__}, payload_keys={payload.keys() if isinstance(payload, dict) else 'N/A'}")
                            
                            if content:
                                preview = content[:150].replace("\n", " ") + ("..." if len(content) > 150 else "")
                                logger.debug(f"[AGENDA GEN] Project {project_id} doc {idx} preview: {preview}")
                                logger.debug(f"[AGENDA GEN] Project {project_id} doc {idx} FULL CONTENT:\n{content}")
                                documents.append(content)
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
            raise HTTPException(status_code=400, detail="No documents available to generate agenda. Please upload files.")

        # Step 4: Call agenda generator with documents only
        total_chars = sum(len(doc) for doc in documents)
        logger.info(f"[AGENDA GEN] Context ready for meeting {meeting_id}: {len(documents)} documents ({total_chars} total chars)")
        logger.info(f"[AGENDA GEN] Starting LLM agenda generation for meeting {meeting_id}")
        model = _get_model()

        agenda_content, token_usage = asyncio.run(
            generate_agenda_from_documents(
                documents=documents,
                model=model,
                meeting_type_hint=meeting_type_hint,
                custom_prompt=custom_prompt,
            )
        )

        # Step 5: Save to database using helper function
        result = save_meeting_agenda_results(
            db=db,
            meeting_id=meeting_id,
            user_id=user_id,
            agenda_content=agenda_content,
            token_usage=token_usage,
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
            token_usage=token_usage if isinstance(token_usage, dict) else None,
        )

    except Exception as e:
        logger.error(f"Error generating agenda for meeting {meeting_id}: {e}")
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail="Failed to generate agenda. Please try again.")
