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


class ConversationTurn(BaseModel):
    """Individual conversation turn"""
    timestamp: float
    user: str
    ai: str


class ConversationHistory(BaseModel):
    """Conversation history for a session"""
    session_id: str
    turns: List[ConversationTurn]
    total_turns: int


class RAGChatRequest(BaseModel):
    """RAG chat request schema"""
    query: str
    top_k: Optional[int] = 5
    session_id: Optional[str] = None


class RAGChatResponse(BaseModel):
    """RAG chat response schema"""
    response: str
    query: str
    session_id: Optional[str] = None
    metadata: Dict[str, Any]


class CorpusSearchRequest(BaseModel):
    """Corpus search request schema"""
    query: str
    collection_name: Optional[str] = "vietnam_history"
    top_k: Optional[int] = 5


class CorpusResult(BaseModel):
    """Individual corpus search result"""
    rank: int
    score: float
    text: str
    section: Optional[str] = None
    source_file: Optional[str] = None
    word_count: Optional[int] = None
    chunk_index: Optional[int] = None
    total_chunks: Optional[int] = None
    document_type: Optional[str] = None
    topic: Optional[str] = None


class CorpusSearchResponse(BaseModel):
    """Corpus search response schema"""
    query: str
    collection_name: str
    results: List[CorpusResult]
    total_results: int


class WorkflowStatus(BaseModel):
    """LangGraph workflow status"""
    langchain_available: bool
    langgraph_available: bool
    google_client_available: bool
    chat_client_available: bool
    workflow_initialized: bool
    rag_app_compiled: bool
    embedding_dimension: int
    conversation_sessions: int


class CorpusStatistics(BaseModel):
    """Corpus statistics"""
    collection_name: str
    total_vectors: int
    dimension: int
    status: str
    total_chunks: int
    unique_sections: int
    source_files: List[str]
    total_words: int
    avg_chunk_size: int
    language: str
    document_type: str


# API Response types
SearchApiResponse = ApiResponse[SearchResponse]
IndexingStatusResponse = ApiResponse[IndexingStatus]
ConversationHistoryResponse = ApiResponse[ConversationHistory]
RAGChatApiResponse = ApiResponse[RAGChatResponse]
CorpusSearchApiResponse = ApiResponse[CorpusSearchResponse]
WorkflowStatusResponse = ApiResponse[WorkflowStatus]
CorpusStatisticsResponse = ApiResponse[CorpusStatistics]
