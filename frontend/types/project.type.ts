// Project Management Types
// Based on backend schemas from app/schemas/project.py

// Base schemas
export interface ProjectBase {
    name: string;
    description?: string;
}

export type ProjectCreate = ProjectBase;

export interface ProjectUpdate {
    name?: string;
    description?: string;
    is_archived?: boolean;
}

export interface ProjectResponse extends ProjectBase {
    id: string;
    is_archived: boolean;
    created_by: string;
    created_at: string;
    updated_at?: string;
    member_count?: number;
}

export interface ProjectWithMembers extends ProjectResponse {
    members: UserProjectResponse[];
}

// User-Project relationship schemas
export interface UserProjectBase {
    user_id: string;
    project_id: string;
    role: string;
}

export interface UserProjectCreate {
    user_id: string;
    role: string;
}

export interface UserProjectUpdate {
    role: string;
}

export interface UserProjectResponse {
    user_id: string;
    project_id: string;
    role: string;
    joined_at: string;
    user?: any; // User details
}

// Project member management schemas
export interface ProjectMembersResponse {
    project_id: string;
    members: UserProjectResponse[];
    total_count: number;
}

export interface BulkUserProjectCreate {
    users: UserProjectCreate[];
}

export interface BulkUserProjectResponse {
    success: boolean;
    message: string;
    data: any[];
    total_processed: number;
    total_success: number;
    total_failed: number;
}

// Project query/filter schemas
export interface ProjectFilter {
    name?: string;
    is_archived?: boolean;
    created_by?: string;
    member_id?: string;
    created_at_gte?: string;
    created_at_lte?: string;
    page?: number;
    limit?: number;
}

// Query parameters
export interface ProjectQueryParams {
    page?: number;
    limit?: number;
    order_by?: string;
    dir?: 'asc' | 'desc';
    name?: string;
    is_archived?: boolean;
    created_by?: string;
    member_id?: string;
    created_at_gte?: string;
    created_at_lte?: string;
    my_projects_only?: boolean;
}

export interface ProjectMembersQueryParams {
    include_members?: boolean;
}

// API Response Types
export type ProjectApiResponse = ApiResponse<ProjectResponse>;
export type ProjectWithMembersApiResponse = ApiResponse<ProjectWithMembers>;
export type ProjectsPaginatedResponse = PaginatedResponse<ProjectResponse>;
export type ProjectMembersApiResponse = ApiResponse<ProjectMembersResponse>;
export type UserProjectApiResponse = ApiResponse<UserProjectResponse>;

// Project statistics
export interface ProjectStats {
    total_projects: number;
    admin_projects: number;
    member_projects: number;
    active_projects: number;
    archived_projects: number;
}

export type ProjectStatsApiResponse = ApiResponse<ProjectStats>;

// Role change request
export interface RoleChangeRequest {
    role: string;
}

export interface RoleChangeResponse {
    project_id: string;
    current_role: string;
    requested_role: string;
    status: string;
}

export type RoleChangeApiResponse = ApiResponse<RoleChangeResponse>;

// Import common types
import type { ApiResponse, PaginatedResponse } from './common.type';
