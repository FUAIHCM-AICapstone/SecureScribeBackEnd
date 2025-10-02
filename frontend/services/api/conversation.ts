import type {
    ConversationCreate,
    ConversationResponse,
    ConversationUpdate,
    ConversationWithMessagesResponse,
    ConversationsPaginatedResponse
} from '../../types/conversation.type';
import axiosInstance from './axiosInstance';
import { ApiWrapper, QueryBuilder } from './utilities';

/**
 * Create a new conversation
 */
export const createConversation = async (
    conversationData: ConversationCreate
): Promise<ConversationResponse> => {
    return ApiWrapper.execute(() =>
        axiosInstance.post('/conversations', conversationData)
    );
};

/**
 * Get user's conversations with pagination
 */
export const getConversations = async (
    page: number = 1,
    limit: number = 20
): Promise<ConversationsPaginatedResponse> => {
    const queryParams = {
        page,
        limit,
    };

    const queryString = QueryBuilder.build(queryParams);

    return ApiWrapper.execute(() =>
        axiosInstance.get(`/conversations${queryString}`)
    );
};

/**
 * Get a specific conversation
 */
export const getConversation = async (
    conversationId: string
): Promise<ConversationResponse> => {
    return ApiWrapper.execute(() =>
        axiosInstance.get(`/conversations/${conversationId}`)
    );
};

/**
 * Update a conversation
 */
export const updateConversation = async (
    conversationId: string,
    updateData: ConversationUpdate
): Promise<ConversationResponse> => {
    return ApiWrapper.execute(() =>
        axiosInstance.put(`/conversations/${conversationId}`, updateData)
    );
};

/**
 * Delete a conversation (soft delete)
 */
export const deleteConversation = async (
    conversationId: string
): Promise<void> => {
    return ApiWrapper.execute(() =>
        axiosInstance.delete(`/conversations/${conversationId}`)
    );
};

/**
 * Get a conversation with its messages
 */
export const getConversationWithMessages = async (
    conversationId: string,
    limit: number = 50
): Promise<ConversationWithMessagesResponse> => {
    const queryParams = {
        limit,
    };

    const queryString = QueryBuilder.build(queryParams);

    return ApiWrapper.execute(() =>
        axiosInstance.get(`/conversations/${conversationId}/messages${queryString}`)
    );
};

