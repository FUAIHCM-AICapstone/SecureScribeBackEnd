// Task Management Types
// Based on backend schemas from app/schemas/task.py

import type { ApiResponse, PaginatedResponse, BulkResponse } from './common.type';
import type { User } from './user.type';
import type { ProjectResponse } from './project.type';

// Status values supported by backend
export type TaskStatus = 'todo' | 'in_progress' | 'done';

// Create/Update request schemas
export interface TaskCreate {
    title: string;
    description?: string;
    assignee_id?: string;
    meeting_id?: string;
    project_ids: string[];
    due_date?: string; // ISO 8601 UTC
    reminder_at?: string; // ISO 8601 UTC
}

export interface TaskUpdate {
    title?: string;
    description?: string;
    assignee_id?: string;
    status?: TaskStatus;
    due_date?: string; // ISO 8601 UTC
    reminder_at?: string; // ISO 8601 UTC
}

// Response schema
export interface TaskResponse {
    id: string;
    title: string;
    description?: string;
    status: TaskStatus;
    creator_id: string;
    assignee_id?: string;
    meeting_id?: string;
    due_date?: string;
    reminder_at?: string;
    created_at: string;
    updated_at?: string;

    // Expanded relations (optional)
    creator?: User;
    assignee?: User;
    projects?: ProjectResponse[];
}

// Filters and query params
export interface TaskFilter {
    title?: string;
    status?: TaskStatus;
    creator_id?: string;
    assignee_id?: string;
    due_date_gte?: string;
    due_date_lte?: string;
    created_at_gte?: string;
    created_at_lte?: string;
}

export interface TaskQueryParams {
    page?: number;
    limit?: number;
}

// Bulk operations
export interface BulkTaskCreate {
    tasks: TaskCreate[];
}

export interface BulkTaskUpdateItem {
    id: string;
    updates: TaskUpdate;
}

export interface BulkTaskUpdate {
    tasks: BulkTaskUpdateItem[];
}

export type BulkTaskDelete = string[];

export type TaskApiResponse = ApiResponse<TaskResponse>;
export type TasksPaginatedResponse = PaginatedResponse<TaskResponse>;
export type BulkTaskResponse = BulkResponse;


