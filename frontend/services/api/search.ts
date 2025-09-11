import axiosInstance from './axiosInstance';
import type {
    SearchRequest,
    SearchApiResponse,
    IndexingStatusResponse,
    ConversationHistoryResponse,
    RAGChatApiResponse,
    RAGChatRequest,
    CorpusSearchApiResponse,
    CorpusSearchRequest,
    WorkflowStatusResponse,
    CorpusStatisticsResponse,
    ReindexApiResponse,
    CorpusIndexingApiResponse,
    ApiResponse,
} from '../../types/search.type';

// Search API functions

// Perform semantic search
export const searchDocuments = async (params: SearchRequest): Promise<SearchApiResponse> => {
    console.log('🔍 Performing semantic search:', params);
    const response = await axiosInstance.post('/search', params);
    return response.data;
};

// Get indexing status for a file
export const getIndexingStatus = async (fileId: string): Promise<IndexingStatusResponse> => {
    console.log('📊 Getting indexing status for file:', fileId);
    const response = await axiosInstance.get(`/search/status/${fileId}`);
    return response.data;
};

// Manually trigger reindexing for a file
export const reindexFile = async (fileId: string): Promise<ReindexApiResponse> => {
    console.log('🔄 Triggering reindex for file:', fileId);
    const response = await axiosInstance.post(`/search/reindex/${fileId}`);
    return response.data;
};

// Find similar files
export const findSimilarFiles = async (fileId: string, limit: number = 10): Promise<SearchApiResponse> => {
    console.log('🔍 Finding similar files for:', fileId);
    const response = await axiosInstance.get(`/search/similar/${fileId}`, {
        params: { limit }
    });
    return response.data;
};

// RAG Chat with AI
export const ragChat = async (params: RAGChatRequest): Promise<RAGChatApiResponse> => {
    console.log('🤖 RAG Chat request:', params);
    const response = await axiosInstance.post('/search/rag-chat', params);
    return response.data;
};

// Search in corpus collections
export const searchCorpus = async (params: CorpusSearchRequest): Promise<CorpusSearchApiResponse> => {
    console.log('📚 Corpus search:', params);
    const response = await axiosInstance.post('/search/corpus', params);
    return response.data;
};

// Conversation History Management
export const getConversationHistory = async (sessionId: string): Promise<ConversationHistoryResponse> => {
    console.log('💬 Getting conversation history:', sessionId);
    const response = await axiosInstance.get(`/search/conversation/${sessionId}`);
    return response.data;
};

export const clearConversationHistory = async (sessionId: string): Promise<ApiResponse<{ session_id: string }>> => {
    console.log('🗑️ Clearing conversation history:', sessionId);
    const response = await axiosInstance.delete(`/search/conversation/${sessionId}`);
    return response.data;
};

// Workflow Status
export const getWorkflowStatus = async (): Promise<WorkflowStatusResponse> => {
    console.log('⚙️ Getting workflow status');
    const response = await axiosInstance.get('/search/workflow/status');
    return response.data;
};

// Corpus Statistics
export const getCorpusStatistics = async (collectionName: string): Promise<CorpusStatisticsResponse> => {
    console.log('📊 Getting corpus statistics:', collectionName);
    const response = await axiosInstance.get(`/search/corpus/stats/${collectionName}`);
    return response.data;
};

// Corpus File Indexing
export const indexCorpusFile = async (
    filePath: string,
    collectionName: string = 'vietnam_history'
): Promise<CorpusIndexingApiResponse> => {
    console.log('📥 Indexing corpus file:', filePath);
    const response = await axiosInstance.post('/search/corpus/index', null, {
        params: { file_path: filePath, collection_name: collectionName }
    });
    return response.data;
};

// Enhanced Search with Filters
export const searchDocumentsAdvanced = async (
    query: string,
    options: {
        limit?: number;
        projectId?: string;
        meetingId?: string;
        fileTypes?: string[];
        dateFrom?: string;
        dateTo?: string;
    } = {}
): Promise<SearchApiResponse> => {
    console.log('🔍 Advanced search:', { query, ...options });

    const params: SearchRequest = {
        query,
        limit: options.limit || 20,
    };

    if (options.projectId) params.project_id = options.projectId;
    if (options.meetingId) params.meeting_id = options.meetingId;

    const response = await axiosInstance.post('/search', params);
    return response.data;
};

// Batch Operations
export const batchReindexFiles = async (fileIds: string[]): Promise<ApiResponse<{ processed: number; failed: number; results: any[] }>> => {
    console.log('🔄 Batch reindexing files:', fileIds.length);

    const results = [];
    let processed = 0;
    let failed = 0;

    for (const fileId of fileIds) {
        try {
            const result = await reindexFile(fileId);
            results.push({ fileId, success: true, result: result.data });
            processed++;
        } catch (error) {
            results.push({ fileId, success: false, error: error instanceof Error ? error.message : 'Unknown error' });
            failed++;
        }
    }

    return {
        success: true,
        message: `Batch reindexing completed: ${processed} processed, ${failed} failed`,
        data: { processed, failed, results }
    };
};

// Utility Functions
export const validateSearchQuery = (query: string): { valid: boolean; message?: string } => {
    if (!query || query.trim().length === 0) {
        return { valid: false, message: 'Query cannot be empty' };
    }

    if (query.length > 1000) {
        return { valid: false, message: 'Query is too long (max 1000 characters)' };
    }

    return { valid: true };
};

export const getSearchSuggestions = async (partialQuery: string): Promise<string[]> => {
    // This would be implemented on the backend
    // For now, return empty array
    console.log('💡 Getting search suggestions for:', partialQuery);
    return [];
};

// Monitoring and Analytics
export const getSearchAnalytics = async (dateRange?: { from: string; to: string }): Promise<ApiResponse<{
    total_searches: number;
    avg_response_time: number;
    top_queries: Array<{ query: string; count: number }>;
    search_trends: Array<{ date: string; count: number }>;
}>> => {
    console.log('📈 Getting search analytics');
    const params = dateRange ? { from: dateRange.from, to: dateRange.to } : {};
    const response = await axiosInstance.get('/search/analytics', { params });
    return response.data;
};

// Export all functions
const searchApi = {
    // Core search functions
    searchDocuments,
    searchDocumentsAdvanced,

    // Indexing functions
    getIndexingStatus,
    reindexFile,
    findSimilarFiles,
    batchReindexFiles,

    // AI and RAG functions
    ragChat,
    getConversationHistory,
    clearConversationHistory,

    // Corpus functions
    searchCorpus,
    getCorpusStatistics,
    indexCorpusFile,

    // System functions
    getWorkflowStatus,

    // Utility functions
    validateSearchQuery,
    getSearchSuggestions,
    getSearchAnalytics,
};

export default searchApi;
