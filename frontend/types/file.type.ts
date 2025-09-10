// File Management Types
// Based on backend schemas from app/schemas/file.py

export interface FileBase {
    filename?: string;
    mime_type?: string;
    size_bytes?: number;
    file_type?: string;
    project_id?: string;
    meeting_id?: string;
}

export type FileCreate = FileBase;

export interface FileUpdate {
    filename?: string;
    file_type?: string;
}

export interface FileResponse extends FileBase {
    id: string;
    storage_url?: string;
    uploaded_by?: string;
    extracted_text?: string;
    created_at: string;
    updated_at?: string;
}

export interface FileWithProject extends FileResponse {
    project_name?: string;
    can_access: boolean;
}

export interface FileWithMeeting extends FileResponse {
    meeting_title?: string;
    can_access: boolean;
}

export interface FileFilter {
    filename?: string;
    mime_type?: string;
    file_type?: string;
    project_id?: string;
    meeting_id?: string;
    uploaded_by?: string;
    page?: number;
    limit?: number;
}

export interface BulkFileOperation {
    file_ids: string[];
    operation: "delete" | "move";
    target_project_id?: string;
    target_meeting_id?: string;
}

export interface BulkFileResponse {
    success: boolean;
    message: string;
    data: any[];
    total_processed: number;
    total_success: number;
    total_failed: number;
}

// API Response Types
export type FileApiResponse = ApiResponse<FileResponse>;
export type FileWithProjectApiResponse = ApiResponse<FileWithProject>;
export type FileWithMeetingApiResponse = ApiResponse<FileWithMeeting>;
export type FilesPaginatedResponse = PaginatedResponse<FileResponse>;
export type FilesWithProjectPaginatedResponse = PaginatedResponse<FileWithProject>;
export type FilesWithMeetingPaginatedResponse = PaginatedResponse<FileWithMeeting>;

// Upload types for frontend
export interface FileUploadData {
    file: File;
    project_id?: string;
    meeting_id?: string;
}

// File move request
export interface FileMoveRequest {
    project_id?: string;
    meeting_id?: string;
}

// Query parameters for file endpoints
export interface FileQueryParams {
    page?: number;
    limit?: number;
    filename?: string;
    file_type?: string;
    project_id?: string;
    meeting_id?: string;
    uploaded_by?: string;
}

// Import common types
import type { ApiResponse, PaginatedResponse } from './common.type';
