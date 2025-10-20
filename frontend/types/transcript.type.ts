// Transcript Management Types
// Based on backend schemas from app/schemas/transcript.py

export interface TranscriptCreate {
    meeting_id: string;
    content?: string;
    audio_concat_file_id?: string;
}

export interface TranscriptUpdate {
    content?: string;
    extracted_text_for_search?: string;
    qdrant_vector_id?: string;
}

export interface TranscriptResponse {
    id: string;
    meeting_id: string;
    content?: string;
    audio_concat_file_id?: string;
    extracted_text_for_search?: string;
    qdrant_vector_id?: string;
    created_at: string;
    updated_at?: string;
}

export interface TranscriptsPaginatedResponse {
    data: TranscriptResponse[];
    pagination: {
        page: number;
        limit: number;
        total: number;
        pages: number;
    };
}

// Import common types
import type { ApiResponse } from './common.type';

export type TranscriptApiResponse = ApiResponse<TranscriptResponse>;
export type TranscriptsPaginatedApiResponse = ApiResponse<TranscriptsPaginatedResponse>;
