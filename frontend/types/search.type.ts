// Search Types
export interface SearchRequest {
    query: string;
    limit?: number;
    project_id?: string;
    meeting_id?: string;
}

export interface SearchResult {
    file_id: string;
    chunk_index: number;
    text: string;
    score: number;
    chunk_size: number;
    filename?: string;
    mime_type?: string;
}

export interface SearchResponse {
    query: string;
    results: SearchResult[];
    total_results: number;
    search_time: number;
}

export interface IndexingStatus {
    file_id: string;
    status: 'not_started' | 'in_progress' | 'completed' | 'failed';
    progress: number;
    message?: string;
    filename?: string;
    mime_type?: string;
}

// Task Progress Types
export interface TaskProgressData {
    task_id: string;
    progress: number;
    status: string;
    estimated_time: string;
    last_update: string;
    task_type: string;
}

export interface TaskProgressMessage {
    type: 'task_progress';
    data: TaskProgressData;
}

// WebSocket Message Types
export type WebSocketMessage = TaskProgressMessage | {
    type: string;
    data: any;
};

// Common API Response (matches backend ApiResponse)
export interface ApiResponse<T> {
    success: boolean;
    message?: string;
    data?: T;
}

// Indexing Types
export interface IndexingProgress {
    file_id: string;
    status: 'started' | 'extracting' | 'chunking' | 'embedding' | 'storing' | 'completed' | 'failed';
    progress: number;
    message: string;
    current_step?: string;
    total_chunks?: number;
    processed_chunks?: number;
}

export interface IndexingStatusExtended {
    file_id: string;
    status: 'not_started' | 'in_progress' | 'completed' | 'failed';
    progress: number;
    message?: string;
    started_at?: string;
    completed_at?: string;
}

// Conversation Types
export interface ConversationTurn {
    timestamp: number;
    user: string;
    ai: string;
}

export interface ConversationHistory {
    session_id: string;
    turns: ConversationTurn[];
    total_turns: number;
}

// RAG Chat Types
export interface RAGChatRequest {
    query: string;
    top_k?: number;
    session_id?: string;
}

export interface RAGChatResponse {
    response: string;
    query: string;
    session_id?: string;
    metadata: {
        document_count: number;
        has_conversation_context: boolean;
    };
}

// Corpus Types
export interface CorpusSearchRequest {
    query: string;
    collection_name?: string;
    top_k?: number;
}

export interface CorpusResult {
    rank: number;
    score: number;
    text: string;
    section?: string;
    source_file?: string;
    word_count?: number;
    chunk_index?: number;
    total_chunks?: number;
    document_type?: string;
    topic?: string;
}

export interface CorpusSearchResponse {
    query: string;
    collection_name: string;
    results: CorpusResult[];
    total_results: number;
}

// Workflow Types
export interface WorkflowStatus {
    google_client_available: boolean;
    chat_client_available: boolean;
    workflow_initialized: boolean;
    rag_app_compiled: boolean;
    embedding_dimension: number;
    conversation_sessions: number;
}

// Corpus Statistics Types
export interface CorpusStatistics {
    collection_name: string;
    total_vectors: number;
    dimension: number;
    status: string;
    total_chunks: number;
    unique_sections: number;
    source_files: string[];
    total_words: number;
    avg_chunk_size: number;
    language: string;
    document_type: string;
}

// Reindex Types
export interface ReindexResponse {
    file_id: string;
    filename: string;
    status: string;
}

// Corpus Indexing Types
export interface CorpusIndexingRequest {
    file_path: string;
    collection_name?: string;
}

export interface CorpusIndexingResponse {
    file_path: string;
    collection_name: string;
}

// Specific Response Types
export type SearchApiResponse = ApiResponse<SearchResponse>;
export type IndexingStatusResponse = ApiResponse<IndexingStatus>;
export type IndexingStatusExtendedResponse = ApiResponse<IndexingStatusExtended>;
export type ConversationHistoryResponse = ApiResponse<ConversationHistory>;
export type RAGChatApiResponse = ApiResponse<RAGChatResponse>;
export type CorpusSearchApiResponse = ApiResponse<CorpusSearchResponse>;
export type WorkflowStatusResponse = ApiResponse<WorkflowStatus>;
export type CorpusStatisticsResponse = ApiResponse<CorpusStatistics>;
export type ReindexApiResponse = ApiResponse<ReindexResponse>;
export type CorpusIndexingApiResponse = ApiResponse<CorpusIndexingResponse>;
