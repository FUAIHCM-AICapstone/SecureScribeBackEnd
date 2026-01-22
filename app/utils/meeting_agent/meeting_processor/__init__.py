from __future__ import annotations

import asyncio
from typing import Any, Dict, Iterable, List, Optional

from app.utils.meeting_agent.agent_schema import MeetingOutput, Task

from .note_generator import NoteGenerator
from .task_extractor import TaskExtractor

__all__ = ["MeetingProcessor"]


class MeetingProcessor:
    """Co-ordinate meeting processing with concurrent execution."""

    def __init__(self, model: Any) -> None:
        self._model = model
        self._task_extractor = TaskExtractor(self._model)
        self._note_generator = NoteGenerator(self._model)

    async def process_meeting(
        self,
        transcript: str,
        custom_prompt: Optional[str] = None,
        meeting_id: Optional[str] = None,
        user_id: Optional[str] = None,
        db: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Process meeting transcript with concurrent task extraction and note generation.

        Args:
            transcript: Meeting transcript text
            custom_prompt: Optional custom prompt for note generation
            meeting_id: Meeting ID for retrieving related documents/agenda
            user_id: User ID for authorization
            db: Database session for querying

        Returns:
            Dictionary containing meeting_note, task_items, is_informative, meeting_type
        """
        transcript_value = transcript or ""

        # Step 1: Simple validation
        if not self._simple_validation(transcript_value):
            return self._format_failure("Transcript validation failed: too short or empty")

        # Step 2: Concurrent extraction with error handling
        try:
            results = await asyncio.gather(
                self._extract_tasks_with_retry(transcript_value),
                self._generate_note_with_retry(
                    transcript_value,
                    custom_prompt,
                    meeting_id=meeting_id,
                    user_id=user_id,
                    db=db,
                ),
                return_exceptions=True,  # Continue even if one fails
            )

            tasks_result = results[0]
            note_result = results[1]

            # Handle partial failures
            if isinstance(tasks_result, Exception):
                tasks_result = []  # Empty list as fallback

            if isinstance(note_result, Exception):
                note_result = ("Không thể tạo ghi chú cuộc họp do lỗi xử lý.", {})  # Fallback with empty tokens

            # Unpack note and tokens
            if isinstance(note_result, tuple):
                note_text, token_usage = note_result
            else:
                note_text = note_result
                token_usage = {}

        except Exception as exc:
            return self._format_failure(str(exc))

        # Step 3: Format and return success
        return self._format_success(tasks_result, note_text, token_usage)

    def _simple_validation(self, transcript: str) -> bool:
        """
        Simple validation without LLM call.

        Args:
            transcript: Transcript text to validate

        Returns:
            True if valid, False otherwise
        """
        if not transcript or not transcript.strip():
            return False

        if len(transcript.strip()) < 100:
            return False

        return True

    async def _extract_tasks_with_retry(self, transcript: str) -> List[Task]:
        """
        Extract tasks with built-in retry logic.

        Args:
            transcript: Meeting transcript

        Returns:
            List of extracted tasks (empty list on failure after retries)
        """
        try:
            tasks = await self._task_extractor.extract(transcript)
            return tasks
        except Exception:
            return []  # Return empty list as fallback

    async def _generate_note_with_retry(
        self,
        transcript: str,
        custom_prompt: Optional[str] = None,
        meeting_id: Optional[str] = None,
        user_id: Optional[str] = None,
        db: Optional[Any] = None,
    ) -> tuple[str, dict]:
        """
        Generate meeting note with built-in retry logic and sliding window extraction.

        Flow:
        1. Extract important notes from transcript chunks (sliding window with token tracking)
        2. Retrieve full agenda (no sliding window)
        3. Retrieve project files and extract important notes (sliding window)
        4. Retrieve meeting files and extract important notes (sliding window)
        5. Merge all token usage
        6. Generate note with all contexts

        Args:
            transcript: Meeting transcript
            custom_prompt: Optional custom prompt
            meeting_id: Meeting ID
            user_id: User ID
            db: Database session

        Returns:
            Tuple of (generated note, merged token_usage dict)
        """
        try:
            from app.crud.meeting_agenda import crud_get_meeting_agenda
            from app.services.qdrant_service import (
                query_documents_by_meeting_id,
                query_documents_by_project_id,
            )
            from app.utils.logging import logger
            from app.utils.sliding_window import extract_important_notes_from_chunk

            total_tokens = {
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
            }

            # Step 1: Extract important notes from transcript chunks (sliding window)
            logger.info("[NOTE_GEN] Step 1: Extracting important notes from transcript chunks")
            transcript_notes = []
            transcript_chunk_size = 3000
            overlap = 300

            for i in range(0, len(transcript), transcript_chunk_size - overlap):
                chunk = transcript[i : i + transcript_chunk_size]
                if len(chunk.strip()) < 50:
                    continue

                chunk_notes, chunk_tokens = await extract_important_notes_from_chunk(chunk)
                transcript_notes.extend(chunk_notes)

                # Accumulate tokens
                total_tokens["input_tokens"] += chunk_tokens.get("input_tokens", 0)
                total_tokens["output_tokens"] += chunk_tokens.get("output_tokens", 0)
                total_tokens["total_tokens"] += chunk_tokens.get("total_tokens", 0)

                logger.debug(f"[NOTE_GEN] Transcript chunk extracted {len(chunk_notes)} notes")

            logger.info(f"[NOTE_GEN] Extracted {len(transcript_notes)} important notes from transcript chunks")
            transcript_context = "\n".join(transcript_notes) if transcript_notes else ""

            # Step 2: Retrieve full agenda (no sliding window, full context)
            logger.info("[NOTE_GEN] Step 2: Retrieving full agenda")
            agenda_content = ""
            if meeting_id and db:
                try:
                    agenda_obj = crud_get_meeting_agenda(db, int(meeting_id))
                    if agenda_obj and agenda_obj.content:
                        agenda_content = agenda_obj.content
                        logger.info(f"[NOTE_GEN] Retrieved agenda ({len(agenda_content)} chars)")
                except Exception as e:
                    logger.warning(f"[NOTE_GEN] Could not retrieve agenda: {e}")

            # Step 3: Extract important notes from project files (sliding window)
            logger.info("[NOTE_GEN] Step 3: Extracting important notes from project files")
            project_files_context = ""
            if meeting_id and user_id and db:
                try:
                    from app.services.meeting import get_meeting

                    # Get meeting's projects
                    meeting = get_meeting(db, int(meeting_id), int(user_id))
                    if meeting and hasattr(meeting, "projects"):
                        project_ids = [pm.project_id for pm in meeting.projects if pm.project]

                        project_file_notes = []
                        for project_id in project_ids:
                            logger.debug(f"[NOTE_GEN] Querying project {project_id} files")
                            project_docs = await query_documents_by_project_id(str(project_id), top_k=3, db=db, user_id=str(user_id))

                            for doc in project_docs or []:
                                content = None
                                existing_notes = None
                                point_id = None
                                if isinstance(doc, dict):
                                    payload = doc.get("payload") or {}
                                    content = payload.get("text") or doc.get("content")
                                    existing_notes = payload.get("important_notes")
                                    point_id = doc.get("id")
                                else:
                                    payload = getattr(doc, "payload", None) or {}
                                    if isinstance(payload, dict):
                                        content = payload.get("text")
                                        existing_notes = payload.get("important_notes")
                                    if not content:
                                        content = getattr(doc, "content", None)
                                    point_id = getattr(doc, "id", None)

                                if content and len(content.strip()) > 50:
                                    notes, file_tokens = await extract_important_notes_from_chunk(content, existing_notes=existing_notes)
                                    project_file_notes.extend(notes)

                                    # Update vector payload if notes were newly extracted (not cached)
                                    if notes and not existing_notes and point_id:
                                        from app.core.config import settings as _settings
                                        from app.utils.qdrant import update_vector_payload

                                        update_vector_payload(
                                            _settings.QDRANT_COLLECTION_NAME,
                                            point_id,
                                            {
                                                "important_notes": notes,
                                                "important_notes_count": len(notes),
                                            },
                                        )

                                    # Accumulate tokens
                                    total_tokens["input_tokens"] += file_tokens.get("input_tokens", 0)
                                    total_tokens["output_tokens"] += file_tokens.get("output_tokens", 0)
                                    total_tokens["total_tokens"] += file_tokens.get("total_tokens", 0)

                        if project_file_notes:
                            project_files_context = "\n".join(project_file_notes)
                            logger.info(f"[NOTE_GEN] Extracted {len(project_file_notes)} notes from project files")
                except Exception as e:
                    logger.warning(f"[NOTE_GEN] Could not retrieve project files: {e}")

            # Step 4: Extract important notes from meeting files (sliding window)
            logger.info("[NOTE_GEN] Step 4: Extracting important notes from meeting files")
            meeting_files_context = ""
            if meeting_id and user_id and db:
                try:
                    logger.debug(f"[NOTE_GEN] Querying meeting {meeting_id} files (top 7)")
                    meeting_docs = await query_documents_by_meeting_id(str(meeting_id), top_k=7, db=db, user_id=str(user_id))

                    meeting_file_notes = []
                    for doc in meeting_docs or []:
                        content = None
                        existing_notes = None
                        point_id = None
                        if isinstance(doc, dict):
                            payload = doc.get("payload") or {}
                            content = payload.get("text") or doc.get("content")
                            existing_notes = payload.get("important_notes")
                            point_id = doc.get("id")
                        else:
                            payload = getattr(doc, "payload", None) or {}
                            if isinstance(payload, dict):
                                content = payload.get("text")
                                existing_notes = payload.get("important_notes")
                            if not content:
                                content = getattr(doc, "content", None)
                            point_id = getattr(doc, "id", None)

                        if content and len(content.strip()) > 50:
                            notes, file_tokens = await extract_important_notes_from_chunk(content, existing_notes=existing_notes)
                            meeting_file_notes.extend(notes)

                            # Update vector payload if notes were newly extracted (not cached)
                            if notes and not existing_notes and point_id:
                                from app.core.config import settings as _settings
                                from app.utils.qdrant import update_vector_payload

                                update_vector_payload(
                                    _settings.QDRANT_COLLECTION_NAME,
                                    point_id,
                                    {
                                        "important_notes": notes,
                                        "important_notes_count": len(notes),
                                    },
                                )

                            # Accumulate tokens
                            total_tokens["input_tokens"] += file_tokens.get("input_tokens", 0)
                            total_tokens["output_tokens"] += file_tokens.get("output_tokens", 0)
                            total_tokens["total_tokens"] += file_tokens.get("total_tokens", 0)

                    if meeting_file_notes:
                        meeting_files_context = "\n".join(meeting_file_notes)
                        logger.info(f"[NOTE_GEN] Extracted {len(meeting_file_notes)} notes from meeting files")
                except Exception as e:
                    logger.warning(f"[NOTE_GEN] Could not retrieve meeting files: {e}")

            # Step 5: Generate note with all contexts
            logger.info(f"[NOTE_GEN] Generating note with transcript ({len(transcript_context)} chars), agenda ({len(agenda_content)} chars), project_files ({len(project_files_context)} chars), meeting_files ({len(meeting_files_context)} chars)")
            note, note_tokens = await self._note_generator.generate_with_empty_fallback(
                transcript,
                [],
                custom_prompt,
                agenda=agenda_content if agenda_content else None,
                project_files_context=project_files_context if project_files_context else None,
                meeting_files_context=meeting_files_context if meeting_files_context else None,
            )

            # Merge note generation tokens
            total_tokens["input_tokens"] += note_tokens.get("input_tokens", 0)
            total_tokens["output_tokens"] += note_tokens.get("output_tokens", 0)
            total_tokens["total_tokens"] += note_tokens.get("total_tokens", 0)

            logger.info(f"[NOTE_GEN] Total token usage: {total_tokens}")
            return note, total_tokens

        except Exception as e:
            print(f"[NOTE_GEN] Error generating note: {e}")
            return "Không thể tạo ghi chú cuộc họp do lỗi xử lý.", {
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
            }

    def _format_success(self, tasks: List[Task], note: str, token_usage: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format successful processing result.

        Args:
            tasks: List of extracted tasks
            note: Generated meeting note
            token_usage: Token usage metrics

        Returns:
            Formatted result dictionary
        """
        # Ensure tasks is a list
        if not isinstance(tasks, list):
            tasks = []

        # Convert Task objects to dicts
        tasks_list = self._ensure_model_list(tasks, Task)

        output = MeetingOutput(
            meeting_note=note if isinstance(note, str) else "",
            task_items=tasks_list,
            is_informative=True,  # Always true if we got here
            meeting_type="general",  # Always general
        )

        result = output.model_dump()
        result["task_items"] = [task.model_dump() for task in output.task_items]
        result["token_usage"] = token_usage

        return result

    def _format_failure(self, message: str) -> Dict[str, Any]:
        """
        Format failure result.

        Args:
            message: Error message

        Returns:
            Formatted failure dictionary
        """
        return {
            "meeting_note": "",
            "task_items": [],
            "is_informative": False,
            "meeting_type": "general",
        }

    @staticmethod
    def _ensure_model_list(items: Iterable[Any], model_cls: Any) -> list:
        """
        Ensure all items are instances of the model class.

        Args:
            items: Iterable of items
            model_cls: Model class to convert to

        Returns:
            List of model instances
        """
        converted = []
        for item in items:
            if isinstance(item, model_cls):
                converted.append(item)
            elif isinstance(item, dict):
                try:
                    converted.append(model_cls(**item))
                except Exception as exc:
                    print(f"Failed to convert dict to {model_cls.__name__}: {str(exc)}")
        return converted
