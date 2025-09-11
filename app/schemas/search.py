from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from app.schemas.common import ApiResponse


class SearchRequest(BaseModel):
    """Search request schema"""
    query: str
    limit: Optional[int] = 10
    project_id: Optional[str] = None
    meeting_id: Optional[str] = None


class SearchResult(BaseModel):
    """Individual search result"""
    file_id: str
    chunk_index: int
    text: str
    score: float
    chunk_size: int
    filename: Optional[str] = None
    mime_type: Optional[str] = None


class SearchResponse(BaseModel):
    """Search response schema"""
    query: str
    results: List[SearchResult]
    total_results: int
    search_time: float


class IndexingProgress(BaseModel):
    """Indexing progress update"""
    file_id: str
    status: str  # "started", "extracting", "chunking", "embedding", "storing", "completed", "failed"
    progress: int  # 0-100
    message: str
    current_step: Optional[str] = None
    total_chunks: Optional[int] = None
    processed_chunks: Optional[int] = None


class IndexingStatus(BaseModel):
    """Indexing status for a file"""
    file_id: str
    status: str  # "not_started", "in_progress", "completed", "failed"
    progress: int
    message: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None




# API Response types
SearchApiResponse = ApiResponse[SearchResponse]
IndexingStatusResponse = ApiResponse[IndexingStatus]
