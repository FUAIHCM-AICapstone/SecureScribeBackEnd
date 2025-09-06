// Project Management API
// Based on backend endpoints from app/api/endpoints/project.py

import axiosInstance from './axiosInstance';
import { ApiWrapper, QueryBuilder, UuidValidator } from './utilities';
import type {
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
    ProjectWithMembers,
    UserProjectCreate,
    UserProjectUpdate,
    BulkUserProjectCreate,
    BulkUserProjectResponse,
    ProjectFilter,
    ProjectQueryParams,
    ProjectStats,
    RoleChangeRequest,
    RoleChangeResponse,
} from '../../types/project.type';

/**
 * Create a new project
 */
export const createProject = async (
    projectData: ProjectCreate
): Promise<ProjectResponse> => {
    return ApiWrapper.execute(() =>
        axiosInstance.post('/projects', projectData)
    );
};

/**
 * Get all projects with filtering and pagination
 */
export const getProjects = async (
    filters?: ProjectFilter,
    params?: ProjectQueryParams
): Promise<{ data: ProjectResponse[]; pagination: any }> => {
    const queryParams = {
        ...filters,
        ...params,
    };

    const queryString = QueryBuilder.build(queryParams);

    return ApiWrapper.executePaginated(() =>
        axiosInstance.get(`/projects${queryString}`)
    );
};

/**
 * Get a specific project by ID
 */
export const getProject = async (
    projectId: string,
    includeMembers?: boolean
): Promise<ProjectWithMembers> => {
    UuidValidator.validate(projectId, 'Project ID');

    const queryParams = {
        include_members: includeMembers,
    };

    const queryString = QueryBuilder.build(queryParams);

    return ApiWrapper.execute(() =>
        axiosInstance.get(`/projects/${projectId}${queryString}`)
    );
};

/**
 * Update a project
 */
export const updateProject = async (
    projectId: string,
    updates: ProjectUpdate
): Promise<ProjectResponse> => {
    UuidValidator.validate(projectId, 'Project ID');

    return ApiWrapper.execute(() =>
        axiosInstance.put(`/projects/${projectId}`, updates)
    );
};

/**
 * Delete a project
 */
export const deleteProject = async (projectId: string): Promise<void> => {
    UuidValidator.validate(projectId, 'Project ID');

    return ApiWrapper.executeVoid(() =>
        axiosInstance.delete(`/projects/${projectId}`)
    );
};

/**
 * Add a user to a project
 */
export const addUserToProject = async (
    projectId: string,
    userData: UserProjectCreate
): Promise<any> => {
    UuidValidator.validate(projectId, 'Project ID');
    UuidValidator.validate(userData.user_id, 'User ID');

    return ApiWrapper.execute(() =>
        axiosInstance.post(`/projects/${projectId}/members`, userData)
    );
};

/**
 * Remove a user from a project
 */
export const removeUserFromProject = async (
    projectId: string,
    userId: string
): Promise<void> => {
    UuidValidator.validate(projectId, 'Project ID');
    UuidValidator.validate(userId, 'User ID');

    return ApiWrapper.executeVoid(() =>
        axiosInstance.delete(`/projects/${projectId}/members/${userId}`)
    );
};

/**
 * Update user role in project
 */
export const updateUserRole = async (
    projectId: string,
    userId: string,
    roleUpdate: UserProjectUpdate
): Promise<any> => {
    UuidValidator.validate(projectId, 'Project ID');
    UuidValidator.validate(userId, 'User ID');

    return ApiWrapper.execute(() =>
        axiosInstance.put(`/projects/${projectId}/members/${userId}`, roleUpdate)
    );
};

/**
 * Bulk add users to project
 */
export const bulkAddUsersToProject = async (
    projectId: string,
    bulkData: BulkUserProjectCreate
): Promise<BulkUserProjectResponse> => {
    UuidValidator.validate(projectId, 'Project ID');

    // Validate user IDs in bulk data
    bulkData.users.forEach((user, index) => {
        UuidValidator.validate(user.user_id, `User ID at index ${index}`);
    });

    return ApiWrapper.executeBulk(() =>
        axiosInstance.post(`/projects/${projectId}/members/bulk`, bulkData)
    );
};

/**
 * Bulk remove users from project
 */
export const bulkRemoveUsersFromProject = async (
    projectId: string,
    userIds: string[]
): Promise<BulkUserProjectResponse> => {
    UuidValidator.validate(projectId, 'Project ID');

    // Validate all user IDs
    userIds.forEach((id, index) => {
        UuidValidator.validate(id, `User ID at index ${index}`);
    });

    const queryString = QueryBuilder.build({
        user_ids: userIds.join(','),
    });

    return ApiWrapper.executeBulk(() =>
        axiosInstance.delete(`/projects/${projectId}/members/bulk${queryString}`)
    );
};

/**
 * Get current user's project statistics
 */
export const getMyProjectStats = async (): Promise<ProjectStats> => {
    return ApiWrapper.execute(() =>
        axiosInstance.get('/users/me/project-stats')
    );
};

/**
 * Request role change in project
 */
export const requestRoleChange = async (
    projectId: string,
    roleRequest: RoleChangeRequest
): Promise<RoleChangeResponse> => {
    UuidValidator.validate(projectId, 'Project ID');

    return ApiWrapper.execute(() =>
        axiosInstance.post(`/projects/${projectId}/me/request-role`, roleRequest)
    );
};

// Convenience functions for common operations
export const getMyProjects = async (
    params?: Omit<ProjectQueryParams, 'my_projects_only'>
): Promise<{ data: ProjectResponse[]; pagination: any }> => {
    return getProjects({}, { ...params, my_projects_only: true });
};

export const getActiveProjects = async (
    params?: Omit<ProjectQueryParams, 'is_archived'>
): Promise<{ data: ProjectResponse[]; pagination: any }> => {
    return getProjects({ is_archived: false }, params);
};

export const getArchivedProjects = async (
    params?: Omit<ProjectQueryParams, 'is_archived'>
): Promise<{ data: ProjectResponse[]; pagination: any }> => {
    return getProjects({ is_archived: true }, params);
};

export const archiveProject = async (projectId: string): Promise<ProjectResponse> => {
    return updateProject(projectId, { is_archived: true });
};

export const unarchiveProject = async (projectId: string): Promise<ProjectResponse> => {
    return updateProject(projectId, { is_archived: false });
};

export const changeUserRoleToAdmin = async (
    projectId: string,
    userId: string
): Promise<any> => {
    return updateUserRole(projectId, userId, { role: 'admin' });
};

export const changeUserRoleToMember = async (
    projectId: string,
    userId: string
): Promise<any> => {
    return updateUserRole(projectId, userId, { role: 'member' });
};
