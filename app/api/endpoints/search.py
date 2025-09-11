import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import get_db
from app.models.file import File
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.search import (
    ConversationHistoryResponse,
    CorpusSearchApiResponse,
    CorpusSearchRequest,
    CorpusStatisticsResponse,
    IndexingStatusResponse,
    RAGChatApiResponse,
    RAGChatRequest,
    SearchApiResponse,
    SearchRequest,
    SearchResponse,
    SearchResult,
    WorkflowStatusResponse,
)
from app.services.file import check_file_access
from app.services.search import ai_service
from app.utils.auth import get_current_user

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
        # Perform vector search using QdrantService
        from app.services.qdrant_service import qdrant_service
        query_embedding = await ai_service.embed_query(request.query)
        raw_results = await qdrant_service.search_vectors(
            collection="documents",
            query_vector=query_embedding,
            top_k=request.limit or 10
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
            "final_results": 0
        }

        for i, result in enumerate(raw_results):
            try:
                print(f"\033[96m📄 Processing result {i+1}/{len(raw_results)}...\033[0m")

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
                file = db.query(File).filter(File.id == file_id).first()
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

                # Apply project filter if specified
                if request.project_id:
                    if str(file.project_id) != request.project_id:
                        print(f"\033[93m🏢 Project filter: file.project_id={file.project_id} != request.project_id={request.project_id}\033[0m")
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
                    mime_type=file.mime_type
                )
                filtered_results.append(enriched_result)
                print("\033[92m✅ Result added to filtered list\033[0m")

            except Exception as e:
                print(f"\033[91m❌ Error processing search result {i+1}: {e}\033[0m")
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

        print(
            f"\033[92m✅ Search completed: {len(filtered_results)} results found\033[0m"
        )

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
        file = db.query(File).filter(File.id == file_id).first()
        if not file:
            raise HTTPException(status_code=404, detail="File not found")

        if not check_file_access(db, file, current_user.id):
            raise HTTPException(status_code=403, detail="Access denied")

        # Determine indexing status
        if file.qdrant_vector_id:
            status = "completed"
            progress = 100
            message = "File has been indexed successfully"
        elif file.extracted_text:
            status = "in_progress"
            progress = 50
            message = "Text extracted, processing embeddings"
        else:
            status = "not_started"
            progress = 0
            message = "Indexing not yet started"

        print(
            f"\033[93m📈 File {file_id} indexing status: {status} ({progress}%)\033[0m"
        )

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


@router.post("/search/reindex/{file_id}", response_model=ApiResponse[dict])
def reindex_file(
    file_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Manually trigger reindexing for a specific file"""
    print(f"\033[94m🔄 Triggering manual reindex for file {file_id}\033[0m")

    try:
        # Check if file exists and user has access
        file = db.query(File).filter(File.id == file_id).first()
        if not file:
            raise HTTPException(status_code=404, detail="File not found")

        if file.uploaded_by != current_user.id:
            raise HTTPException(
                status_code=403, detail="Only file owner can trigger reindexing"
            )

        # Check if file type is supported
        supported_mimes = [
            "text/plain",
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ]
        if file.mime_type not in supported_mimes:
            raise HTTPException(
                status_code=400,
                detail=f"File type {file.mime_type} is not supported for indexing",
            )

        # Import and trigger indexing task
        from app.jobs.tasks import index_file_task

        try:
            index_file_task.delay(str(file_id), str(current_user.id))
            print(f"\033[92m✅ Reindexing task queued for file {file_id}\033[0m")

            return ApiResponse(
                success=True,
                message="Reindexing task has been queued",
                data={
                    "file_id": str(file_id),
                    "filename": file.filename,
                    "status": "queued",
                },
            )
        except Exception as e:
            print(f"\033[91m❌ Failed to queue reindexing task: {e}\033[0m")
            raise HTTPException(
                status_code=500, detail="Failed to queue reindexing task"
            )

    except HTTPException:
        raise
    except Exception as e:
        print(f"\033[91m❌ Reindexing request failed: {e}\033[0m")
        raise HTTPException(status_code=500, detail=f"Reindexing failed: {str(e)}")


@router.get("/search/similar/{file_id}", response_model=SearchApiResponse)
async def find_similar_files(
    file_id: uuid.UUID,
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Find files similar to the given file"""
    print(f"\033[94m🔍 Finding files similar to {file_id}\033[0m")

    try:
        # Check if file exists and user has access
        file = db.query(File).filter(File.id == file_id).first()
        if not file:
            raise HTTPException(status_code=404, detail="File not found")

        if not check_file_access(db, file, current_user.id):
            raise HTTPException(status_code=403, detail="Access denied")

        # Use extracted text as search query
        if not file.extracted_text:
            raise HTTPException(status_code=400, detail="File has not been indexed yet")

        # Perform search using extracted text as query
        from app.services.qdrant_service import qdrant_service
        query_vector = await ai_service.embed_query(file.extracted_text[:500])
        raw_results_qdrant = await qdrant_service.search_vectors(
            collection="documents",
            query_vector=query_vector,
            top_k=limit
        )

        # Convert Qdrant results to expected format
        raw_results = []
        for result in raw_results_qdrant:
            # Handle ScoredPoint object from Qdrant
            payload = getattr(result, "payload", None) or {}
            score = getattr(result, "score", 0.0)

            # Handle payload - could be dict or other format
            if isinstance(payload, dict):
                file_id_str = payload.get("file_id", "")
                chunk_index = payload.get("chunk_index", 0)
                text = payload.get("text", "")
                chunk_size = payload.get("chunk_size", 0)
            else:
                # Fallback for other payload formats
                file_id_str = getattr(payload, "file_id", "") if hasattr(payload, "file_id") else str(payload)
                chunk_index = getattr(payload, "chunk_index", 0) if hasattr(payload, "chunk_index") else 0
                text = getattr(payload, "text", "") if hasattr(payload, "text") else str(payload)
                chunk_size = getattr(payload, "chunk_size", 0) if hasattr(payload, "chunk_size") else 0

            raw_results.append({
                "file_id": file_id_str,
                "chunk_index": chunk_index,
                "text": text,
                "score": score,
                "chunk_size": chunk_size
            })

        # Filter out the original file and apply access control
        filtered_results = []
        for result in raw_results:
            try:
                result_file_id = uuid.UUID(result["file_id"])

                # Skip the original file
                if result_file_id == file_id:
                    continue

                result_file = db.query(File).filter(File.id == result_file_id).first()
                if not result_file:
                    continue

                # Check access permissions
                if not check_file_access(db, result_file, current_user.id):
                    continue

                # Add file metadata to result
                enriched_result = SearchResult(
                    **result,
                    filename=result_file.filename,
                    mime_type=result_file.mime_type,
                )
                filtered_results.append(enriched_result)

            except Exception as e:
                print(f"\033[91m❌ Error processing similar file result: {e}\033[0m")
                continue

        search_response = SearchResponse(
            query=f"Similar to: {file.filename}",
            results=filtered_results,
            total_results=len(filtered_results),
            search_time=0.0,
        )

        print(f"\033[92m✅ Found {len(filtered_results)} similar files\033[0m")

        return ApiResponse(
            success=True,
            message=f"Found {len(filtered_results)} similar files",
            data=search_response,
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"\033[91m❌ Similar files search failed: {e}\033[0m")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.post("/search/rag-chat", response_model=RAGChatApiResponse)
async def rag_chat(
    request: RAGChatRequest,
    current_user: User = Depends(get_current_user),
):
    """Advanced RAG chat with conversation memory"""
    try:
        response = await ai_service.run_rag_chat(
            query=request.query,
            top_k=request.top_k,
            session_id=request.session_id
        )

        return ApiResponse(
            success=True,
            message="RAG chat response generated",
            data={
                "response": response,
                "query": request.query,
                "session_id": request.session_id,
                "metadata": {}
            },
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG chat failed: {str(e)}")


@router.post("/search/corpus", response_model=CorpusSearchApiResponse)
async def search_corpus(
    request: CorpusSearchRequest,
    current_user: User = Depends(get_current_user),
):
    """Search in specialized corpus collections"""
    try:
        from app.services.qdrant_service import qdrant_service

        if not qdrant_service.ai_service:
            raise HTTPException(status_code=500, detail="AI service not available for corpus search")

        results = await qdrant_service.search_corpus(
            query=request.query,
            collection_name=request.collection_name,
            top_k=request.top_k
        )

        corpus_results = []
        for result in results:
            # Handle ScoredPoint object from Qdrant
            payload = getattr(result, "payload", None) or {}
            score = getattr(result, "score", 0.0)

            # Handle payload - could be dict or other format
            if isinstance(payload, dict):
                corpus_results.append({
                    "rank": len(corpus_results) + 1,  # Add rank based on order
                    "score": score,
                    "text": payload.get("text", ""),
                    "section": payload.get("section", ""),
                    "source_file": payload.get("source_file", ""),
                    "word_count": payload.get("word_count", 0),
                    "chunk_index": payload.get("chunk_index", 0),
                    "total_chunks": payload.get("total_chunks", 0),
                    "document_type": payload.get("document_type", ""),
                    "topic": payload.get("topic", "")
                })
            else:
                # Fallback for other payload formats
                corpus_results.append({
                    "rank": len(corpus_results) + 1,
                    "score": score,
                    "text": getattr(payload, "text", "") if hasattr(payload, "text") else str(payload),
                    "section": getattr(payload, "section", "") if hasattr(payload, "section") else "",
                    "source_file": getattr(payload, "source_file", "") if hasattr(payload, "source_file") else "",
                    "word_count": getattr(payload, "word_count", 0) if hasattr(payload, "word_count") else 0,
                    "chunk_index": getattr(payload, "chunk_index", 0) if hasattr(payload, "chunk_index") else 0,
                    "total_chunks": getattr(payload, "total_chunks", 0) if hasattr(payload, "total_chunks") else 0,
                    "document_type": getattr(payload, "document_type", "") if hasattr(payload, "document_type") else "",
                    "topic": getattr(payload, "topic", "") if hasattr(payload, "topic") else ""
                })

        return ApiResponse(
            success=True,
            message=f"Found {len(corpus_results)} corpus results",
            data={
                "query": request.query,
                "collection_name": request.collection_name,
                "results": corpus_results,
                "total_results": len(corpus_results)
            },
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Corpus search failed: {str(e)}")


@router.get("/search/conversation/{session_id}", response_model=ConversationHistoryResponse)
async def get_conversation_history(
    session_id: str,
    current_user: User = Depends(get_current_user),
):
    """Get conversation history for a session"""
    try:
        history = ai_service.get_conversation_history(session_id)

        conversation_turns = []
        for turn in history:
            conversation_turns.append({
                "timestamp": turn.get("timestamp", 0),
                "user": turn.get("user", ""),
                "ai": turn.get("ai", "")
            })

        return ApiResponse(
            success=True,
            message="Conversation history retrieved",
            data={
                "session_id": session_id,
                "turns": conversation_turns,
                "total_turns": len(conversation_turns)
            },
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get conversation history: {str(e)}")


@router.delete("/search/conversation/{session_id}", response_model=ApiResponse[dict])
async def clear_conversation_history(
    session_id: str,
    current_user: User = Depends(get_current_user),
):
    """Clear conversation history for a session"""
    try:
        ai_service.clear_conversation_history(session_id)

        return ApiResponse(
            success=True,
            message="Conversation history cleared",
            data={"session_id": session_id},
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear conversation history: {str(e)}")


@router.get("/search/workflow/status", response_model=WorkflowStatusResponse)
async def get_workflow_status(
    current_user: User = Depends(get_current_user),
):
    """Get LangGraph workflow status"""
    try:
        status = ai_service.get_workflow_status()

        return ApiResponse(
            success=True,
            message="Workflow status retrieved",
            data=status,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get workflow status: {str(e)}")


@router.get("/search/corpus/stats/{collection_name}", response_model=CorpusStatisticsResponse)
async def get_corpus_statistics(
    collection_name: str,
    current_user: User = Depends(get_current_user),
):
    """Get statistics for a corpus collection"""
    try:
        from app.services.qdrant_service import qdrant_service

        if not qdrant_service.ai_service:
            raise HTTPException(status_code=500, detail="AI service not available for corpus statistics")

        stats = await qdrant_service.get_corpus_statistics(collection_name)

        return ApiResponse(
            success=True,
            message="Corpus statistics retrieved",
            data=stats,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get corpus statistics: {str(e)}")


@router.post("/search/corpus/index", response_model=ApiResponse[dict])
async def index_corpus_file(
    file_path: str = Query(..., description="Path to the corpus file"),
    collection_name: str = Query("vietnam_history", description="Collection name"),
    current_user: User = Depends(get_current_user),
):
    """Index a corpus file using advanced chunking"""
    try:
        from app.services.qdrant_service import qdrant_service

        if not qdrant_service.ai_service:
            raise HTTPException(status_code=500, detail="AI service not available for corpus indexing")

        # Generate a file_id for corpus files (use filename as ID)
        import os
        corpus_file_id = os.path.basename(file_path)

        success = await qdrant_service.process_file(
            file_path=file_path,
            collection_name=collection_name,
            file_id=corpus_file_id
        )

        if success:
            return ApiResponse(
                success=True,
                message="Corpus file indexed successfully",
                data={
                    "file_path": file_path,
                    "collection_name": collection_name
                },
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to index corpus file")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Corpus indexing failed: {str(e)}")
