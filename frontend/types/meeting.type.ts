// Meeting Management Types
// Based on backend schemas from app/schemas/meeting.py

import type { ApiResponse, PaginatedResponse } from './common.type';
import type { TranscriptResponse } from './transcript.type';
import type { MeetingNoteResponse } from './meeting_note.type';

export interface ProjectResponse {
    id: string;
    name: string;
    description?: string;
    is_archived: boolean;
    created_at: string;
    updated_at?: string;
}

export interface MeetingCreate {
    title?: string;
    description?: string;
    url?: string;
    start_time?: string;
    is_personal: boolean;
    project_ids: string[];
}

export interface MeetingUpdate {
    title?: string;
    description?: string;
    url?: string;
    start_time?: string;
    status?: string;
}

export interface MeetingFilter {
    title?: string;
    description?: string;
    url?: string;
    start_time_gte?: string;
    start_time_lte?: string;
    status?: string;
    is_personal?: boolean;
    created_by?: string;
    project_id?: string;
    tag_ids?: string[];
    page?: number;
    limit?: number;
}

export interface MeetingResponse {
    id: string;
    title?: string;
    description?: string;
    url?: string;
    start_time?: string;
    created_by: string;
    is_personal: boolean;
    status: string;
    is_deleted: boolean;
    created_at: string;
    updated_at?: string;
    projects: ProjectResponse[];
    can_access: boolean;
}

export interface MeetingWithProjects extends MeetingResponse {
    project_count: number;
    member_count: number;
    meeting_note?: MeetingNoteResponse | null;
    transcripts?: TranscriptResponse[];
}

// API Response Types
export type MeetingApiResponse = ApiResponse<MeetingResponse>;
export type MeetingsPaginatedResponse = PaginatedResponse<MeetingResponse>;
export type MeetingWithProjectsApiResponse = ApiResponse<MeetingWithProjects>;

// Query parameters for meeting endpoints
export interface MeetingQueryParams {
    page?: number;
    limit?: number;
    title?: string;
    status?: string;
    is_personal?: boolean;
    created_by?: string;
    tag_ids?: string;
}

// Re-export Meeting Note Types from meeting_note.type for backward compatibility
export type { MeetingNoteResponse, MeetingNoteRequest, MeetingNoteSummaryResponse } from './meeting_note.type';

export const PREDEFINED_SECTIONS = [
    'Key Points',
    'Action Items',
    'Decisions',
    'Discussion',
    'Follow-up',
    'Attendees',
    'Agenda',
];
