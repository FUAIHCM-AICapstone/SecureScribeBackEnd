import { ChatMessageResponse } from './chat.type';

export interface ConversationCreate {
    title?: string;
}

export interface ConversationUpdate {
    title?: string;
    is_active?: boolean;
}

export interface ConversationResponse {
    id: string; // UUID as string
    user_id: string; // UUID as string
    title?: string;
    created_at: string; // ISO datetime string
    updated_at?: string; // ISO datetime string
    is_active: boolean;
    message_count: number;
}

export interface ConversationWithMessagesResponse {
    id: string; // UUID as string
    user_id: string; // UUID as string
    title?: string;
    created_at: string; // ISO datetime string
    updated_at?: string; // ISO datetime string
    is_active: boolean;
    messages: ChatMessageResponse[];
}

export interface ConversationsPaginatedResponse {
    success: boolean;
    message: string;
    data: ConversationResponse[];
    pagination?: {
        page: number;
        limit: number;
        total: number;
        total_pages: number;
        has_next: boolean;
        has_prev: boolean;
    };
}

export interface ConversationApiResponse {
    success: boolean;
    message: string;
    data: ConversationResponse;
}

export interface ConversationWithMessagesApiResponse {
    success: boolean;
    message: string;
    data: ConversationWithMessagesResponse;
}
