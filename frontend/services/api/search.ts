import axiosInstance from './axiosInstance';
import type {
    SearchRequest,
    SearchApiResponse,
    IndexingStatusResponse,
    ApiResponse,
    RagRequest,
    RagApiResponse,
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

// RAG
export const ragChat = async (payload: RagRequest): Promise<RagApiResponse> => {
    console.log('🤖 RAG chat:', payload);
    const response = await axiosInstance.post('/search/rag', payload);
    return response.data;
};

// Batch Operations - Disabled since reindex functionality was removed
export const batchReindexFiles = async (fileIds: string[]): Promise<ApiResponse<{ processed: number; failed: number; results: any[] }>> => {
    console.log('🔄 Batch reindexing files:', fileIds.length);

    return {
        success: true,
        message: "Reindex functionality has been removed",
        data: { processed: 0, failed: 0, results: [] }
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
    batchReindexFiles,

    // Utility functions
    validateSearchQuery,
    getSearchSuggestions,
    getSearchAnalytics,
};

export default searchApi;
