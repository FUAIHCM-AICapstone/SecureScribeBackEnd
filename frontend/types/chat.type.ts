export interface Mention {
    entity_type: string; // "project", "meeting", "file"
    entity_id: string;   // UUID string
    offset_start: number;
    offset_end: number;
}

export interface ChatMessageCreate {
    content: string;
    mentions?: Mention[];
}

export interface ChatMessageResponse {
    id: string; // UUID as string
    conversation_id: string; // UUID as string
    role: string; // "user", "assistant", "system"
    content: string;
    timestamp: string; // ISO datetime string
    mentions?: Mention[];
}

// Note: Conversation-related types moved to conversation.type.ts
// Chat-specific types remain here

export interface ChatMessageApiResponse {
    success: boolean;
    message: string;
    data: ChatMessageResponse | {
        user_message: ChatMessageResponse;
        ai_message: ChatMessageResponse;
    };
}

// Note: ConversationApiResponse moved to conversation.type.ts
