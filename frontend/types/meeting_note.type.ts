// Meeting Note Management Types
// Based on backend schemas from app/schemas/meeting_note.py

import type { ApiResponse } from './common.type';

export interface MeetingNoteRequest {
    content: string;
}

export interface MeetingNoteResponse {
    id: string;
    content?: string;
    last_edited_at?: string;
    created_at: string;
    updated_at?: string;
}

export interface TaskItem {
    [key: string]: any;
}

export interface DecisionItem {
    [key: string]: any;
}

export interface QuestionItem {
    [key: string]: any;
}

export interface TokenUsage {
    [key: string]: any;
}

export interface MeetingNoteSummaryResponse {
    note: MeetingNoteResponse;
    content: string;
    task_items: TaskItem[];
    decision_items: DecisionItem[];
    question_items: QuestionItem[];
    token_usage: TokenUsage;
}

export interface MeetingNoteCreateParams {
    meeting_id: string;
    custom_prompt?: string;
    meeting_type_hint?: string;
}

export type MeetingNoteApiResponse = ApiResponse<MeetingNoteResponse>;
export type MeetingNoteSummaryApiResponse = ApiResponse<MeetingNoteSummaryResponse>;
