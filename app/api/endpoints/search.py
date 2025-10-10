import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import get_db
from app.models.user import User
from app.schemas.common import ApiResponse, create_pagination_meta
from app.schemas.search import (
    IndexingStatusResponse,
    SearchApiResponse,
    SearchRequest,
    SearchResponse,
    SearchResult,
)
from app.services.file import check_file_access, get_file
from app.services.qdrant_service import build_transcript_search_filter, search_vectors
from app.services.search import search_dynamic
from app.utils.auth import get_current_user
from app.utils.llm import embed_query
from app.utils.qa_workflow import run_rag

router = APIRouter(prefix=settings.API_V1_STR, tags=["Search"])


@router.post("/search", response_model=SearchApiResponse)
async def search_documents(
    request: SearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Perform semantic search across indexed documents"""
    print(f"\033[94m🔍 Starting semantic search for: '{request.query}'\033[0m")

    try:
        # Perform vector search using QdrantService functions

        query_embedding = await embed_query(request.query)
        # Server-side scope filtering in Qdrant
        from qdrant_client.http.models import FieldCondition, Filter, MatchAny, MatchValue
        from app.models.project import Project

        # Build filter that works for both files and transcripts
        qfilter = None
        
        if request.meeting_id:
            # Meeting scope: search both files and transcripts in that meeting
            qfilter = Filter(
                should=[
                    FieldCondition(key="meeting_id", match=MatchValue(value=request.meeting_id)),
                    FieldCondition(key="is_global", match=MatchValue(value=True)),
                ],
                must=[FieldCondition(key="uploaded_by", match=MatchValue(value=str(current_user.id)))],
            )
        elif request.project_id:
            # Project scope: search files by project_id AND transcripts by project_ids array
            qfilter = Filter(
                should=[
                    # Files with this project_id
                    FieldCondition(key="project_id", match=MatchValue(value=request.project_id)),
                    # Transcripts with this project in their project_ids array
                    FieldCondition(key="project_ids", match=MatchAny(any=[request.project_id])),
                    # User's personal items (files uploaded_by or transcripts created_by)
                    FieldCondition(key="uploaded_by", match=MatchValue(value=str(current_user.id))),
                    FieldCondition(key="created_by", match=MatchValue(value=str(current_user.id))),
                ]
            )
        else:
            # No specific scope: get user's accessible projects and build filter
            user_projects = db.query(Project).join(Project.users).filter(
                Project.users.any(id=current_user.id)
            ).all()
            user_project_ids = [str(p.id) for p in user_projects]
            
            if user_project_ids:
                qfilter = build_transcript_search_filter(
                    user_id=str(current_user.id),
                    project_ids=user_project_ids,
                    meeting_id=None,
                    include_personal=True
                )

        raw_results = await search_vectors(
            collection=settings.QDRANT_COLLECTION_NAME,
            query_vector=query_embedding,
            top_k=request.limit or 10,
            query_filter=qfilter,
        )

        # Filter results based on user access and request parameters
        print(f"\033[95m🔍 Starting filtering {len(raw_results)} raw results...\033[0m")
        filtered_results = []

        filter_stats = {
            "total_raw": len(raw_results),
            "no_file_id": 0,
            "invalid_uuid": 0,
            "file_not_found": 0,
            "access_denied": 0,
            "project_filter": 0,
            "meeting_filter": 0,
            "processing_errors": 0,
            "final_results": 0,
        }

        for i, result in enumerate(raw_results):
            try:
                print(f"\033[96m📄 Processing result {i + 1}/{len(raw_results)}...\033[0m")

                # Handle ScoredPoint object from Qdrant
                print(f"\033[94m📊 Result: {result}\033[0m")
                payload = getattr(result, "payload", None) or {}
                score = getattr(result, "score", 0.0)
                print(f"\033[94m📊 Payload type: {type(payload)}, Score: {score:.4f}\033[0m")

                # Handle payload - could be dict or other format
                if isinstance(payload, dict):
                    file_id_str = payload.get("file_id")
                    chunk_index = payload.get("chunk_index", 0)
                    text = payload.get("text", "")
                    chunk_size = payload.get("chunk_size", 0)
                    print(f"\033[94m📋 Dict payload - file_id: {file_id_str}, text_len: {len(text)}\033[0m")
                else:
                    # Fallback for other payload formats
                    file_id_str = getattr(payload, "file_id", None) if hasattr(payload, "file_id") else str(payload)
                    chunk_index = getattr(payload, "chunk_index", 0) if hasattr(payload, "chunk_index") else 0
                    text = getattr(payload, "text", "") if hasattr(payload, "text") else str(payload)
                    chunk_size = getattr(payload, "chunk_size", 0) if hasattr(payload, "chunk_size") else 0
                    print(f"\033[94m📋 Object payload - file_id: {file_id_str}, text_len: {len(text)}\033[0m")

                if not file_id_str:
                    print("\033[93m❌ No file_id found in payload\033[0m")
                    filter_stats["no_file_id"] += 1
                    continue

                # Try to parse UUID
                try:
                    file_id = uuid.UUID(file_id_str)
                    print(f"\033[92m✅ Valid UUID: {file_id}\033[0m")
                except ValueError as e:
                    print(f"\033[93m❌ Invalid UUID format: {file_id_str} - {e}\033[0m")
                    filter_stats["invalid_uuid"] += 1
                    continue

                # Check if file exists in database
                file = get_file(db, file_id)
                if not file:
                    print(f"\033[93m⚠️ File {file_id} not found in database\033[0m")
                    filter_stats["file_not_found"] += 1
                    continue

                print(f"\033[92m📁 File found: {file.filename} ({file.mime_type})\033[0m")

                # Check access permissions
                has_access = check_file_access(db, file, current_user.id)
                if not has_access:
                    print(f"\033[93m🚫 Access denied for file {file_id} (user: {current_user.id})\033[0m")
                    filter_stats["access_denied"] += 1
                    continue

                print("\033[92m✅ Access granted for file\033[0m")

                # Apply project filter if specified (allow user's global files too)
                if request.project_id:
                    is_project_match = str(file.project_id) == request.project_id
                    is_users_global = file.project_id is None and file.meeting_id is None and str(file.uploaded_by or "") == str(current_user.id)
                    if not (is_project_match or is_users_global):
                        print(f"\033[93m🏢 Project filter: excluded file {file.id} (project match={is_project_match}, users_global={is_users_global})\033[0m")
                        filter_stats["project_filter"] += 1
                        continue
                    else:
                        print("\033[92m✅ Project filter passed\033[0m")

                # Apply meeting filter if specified
                if request.meeting_id:
                    if str(file.meeting_id) != request.meeting_id:
                        print(f"\033[93m🏛️ Meeting filter: file.meeting_id={file.meeting_id} != request.meeting_id={request.meeting_id}\033[0m")
                        filter_stats["meeting_filter"] += 1
                        continue
                    else:
                        print("\033[92m✅ Meeting filter passed\033[0m")

                # Convert Qdrant result format to SearchResult format
                enriched_result = SearchResult(
                    file_id=file_id_str,
                    chunk_index=chunk_index,
                    text=text,
                    score=score,
                    chunk_size=chunk_size,
                    filename=file.filename,
                    mime_type=file.mime_type,
                )
                filtered_results.append(enriched_result)
                print("\033[92m✅ Result added to filtered list\033[0m")

            except Exception as e:
                print(f"\033[91m❌ Error processing search result {i + 1}: {e}\033[0m")
                filter_stats["processing_errors"] += 1
                continue

        # Print final filter statistics
        filter_stats["final_results"] = len(filtered_results)
        print("\033[95m📊 FILTER STATISTICS:\033[0m")
        print(f"\033[94m   Total raw results: {filter_stats['total_raw']}\033[0m")
        print(f"\033[93m   - No file_id: {filter_stats['no_file_id']}\033[0m")
        print(f"\033[93m   - Invalid UUID: {filter_stats['invalid_uuid']}\033[0m")
        print(f"\033[93m   - File not found: {filter_stats['file_not_found']}\033[0m")
        print(f"\033[93m   - Access denied: {filter_stats['access_denied']}\033[0m")
        print(f"\033[93m   - Project filter: {filter_stats['project_filter']}\033[0m")
        print(f"\033[93m   - Meeting filter: {filter_stats['meeting_filter']}\033[0m")
        print(f"\033[93m   - Processing errors: {filter_stats['processing_errors']}\033[0m")
        print(f"\033[92m   = Final results: {filter_stats['final_results']}\033[0m")

        search_response = SearchResponse(
            query=request.query,
            results=filtered_results,
            total_results=len(filtered_results),
            search_time=0.0,  # Could be enhanced with actual timing
        )

        print(f"\033[92m✅ Search completed: {len(filtered_results)} results found\033[0m")

        return ApiResponse(
            success=True,
            message=f"Found {len(filtered_results)} matching documents",
            data=search_response,
        )

    except Exception as e:
        print(f"\033[91m❌ Search failed: {e}\033[0m")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/search/status/{file_id}", response_model=IndexingStatusResponse)
def get_indexing_status(
    file_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get indexing status for a specific file"""
    print(f"\033[95m📊 Checking indexing status for file {file_id}\033[0m")

    try:
        # Check if file exists and user has access
        file = get_file(db, file_id)
        if not file:
            raise HTTPException(status_code=404, detail="File not found")

        if not check_file_access(db, file, current_user.id):
            raise HTTPException(status_code=403, detail="Access denied")

        # Determine indexing status
        if file.qdrant_vector_id:
            status = "completed"
            progress = 100
            message = f"File indexed successfully (vector_id: {file.qdrant_vector_id})"
        elif file.extracted_text:
            status = "in_progress"
            progress = 50
            message = "Text extracted, processing embeddings"
        else:
            status = "not_started"
            progress = 0
            message = "Indexing not yet started"

        print(f"\033[93m📈 File {file_id} indexing status: {status} ({progress}%)\033[0m")

        return ApiResponse(
            success=True,
            message="Indexing status retrieved",
            data={
                "file_id": str(file_id),
                "status": status,
                "progress": progress,
                "message": message,
                "filename": file.filename,
                "mime_type": file.mime_type,
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"\033[91m❌ Failed to get indexing status: {e}\033[0m")
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")


@router.post("/search/rag")
async def rag_search(
    request: SearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Minimal RAG endpoint using LangGraph workflow."""
    data = await run_rag(
        request.query,
        db,
        current_user,
        project_id=request.project_id,
        meeting_id=request.meeting_id,
    )
    return ApiResponse(success=True, message="RAG completed", data=data)


@router.get("/search/dynamic", response_model=ApiResponse)
def dynamic_search(
    search: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    page: int = 1,
    limit: int = 20,
):
    """Dynamic search across meetings, projects, and files by title/name/filename."""
    results, total = search_dynamic(db, search, current_user.id, page, limit)
    pagination_meta = create_pagination_meta(page, limit, total)
    return ApiResponse(
        success=True,
        message="Search completed" if results else "No results found.",
        data=results,
        pagination=pagination_meta if results else None,
    )
