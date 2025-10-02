import type {
    ChatConversationResponse,
    ChatMessageCreate,
    ChatMessageResponse,
    ConversationCreate,
    ConversationResponse,
    ConversationsPaginatedResponse,
    Mention
} from '../../types/chat.type';
import axiosInstance from './axiosInstance';
import { ApiWrapper, QueryBuilder, SSEHelper } from './utilities';

/**
 * Create a new conversation (chat session)
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
 * Get a specific conversation (chat session)
 */
export const getConversation = async (
    conversationId: string,
    limit: number = 50
): Promise<ChatConversationResponse> => {
    const queryParams = {
        limit,
    };

    const queryString = QueryBuilder.build(queryParams);

    return ApiWrapper.execute(() =>
        axiosInstance.get(`/conversations/${conversationId}${queryString}`)
    );
};

/**
 * Send a chat message
 */
export const sendChatMessage = async (
    conversationId: string,
    messageData: ChatMessageCreate
): Promise<{
    user_message: ChatMessageResponse;
    ai_message: ChatMessageResponse;
}> => {
    return ApiWrapper.execute(() =>
        axiosInstance.post(`/conversations/${conversationId}/messages`, messageData)
    );
};

/**
 * Connect to SSE for real-time chat messages
 */
export const connectToChatSSE = (
    conversationId: string,
    onMessage: (data: any) => void,
    onError?: (error: any) => void,
    onOpen?: () => void
): EventSource => {
    return SSEHelper.createEventSource(
        `${axiosInstance.defaults.baseURL}/conversations/${conversationId}/events`,
        onMessage,
        onError,
        onOpen
    );
};

/**
 * Disconnect from SSE
 */
export const disconnectFromChatSSE = (eventSource: EventSource): void => {
    SSEHelper.closeEventSource(eventSource);
};

/**
 * Parse mentions from message content
 * Helper function to extract mentions from text like "@project:uuid @meeting:uuid"
 */
export const parseMentions = (content: string): Mention[] => {
    const mentions: Mention[] = [];
    const mentionRegex = /@(\w+):([a-f0-9-]{36})/g;

    let match;
    while ((match = mentionRegex.exec(content)) !== null) {
        mentions.push({
            entity_type: match[1], // project, meeting, file, etc.
            entity_id: match[2],   // UUID
            offset_start: match.index,
            offset_end: match.index + match[0].length,
        });
    }

    return mentions;
};

/**
 * Format message content with mention highlights
 */
export const formatMessageWithMentions = (
    content: string,
    mentions: Mention[]
): string => {
    if (!mentions || mentions.length === 0) {
        return content;
    }

    let formattedContent = content;
    // Sort mentions by offset_start in descending order to avoid index shifting
    const sortedMentions = [...mentions].sort((a, b) => b.offset_start - a.offset_start);

    for (const mention of sortedMentions) {
        const mentionText = content.substring(mention.offset_start, mention.offset_end);
        const entityType = mention.entity_type;
        const entityId = mention.entity_id;

        // Replace mention with highlighted version
        // You can customize the styling here
        const highlightedMention = `<span class="mention mention-${entityType}" data-entity-id="${entityId}">${mentionText}</span>`;
        formattedContent =
            formattedContent.substring(0, mention.offset_start) +
            highlightedMention +
            formattedContent.substring(mention.offset_end);
    }

    return formattedContent;
};
