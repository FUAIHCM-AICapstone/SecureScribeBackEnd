
// File Management API
// Based on backend endpoints from app/api/endpoints/file.py

import axiosInstance from './axiosInstance';
import {
    ApiWrapper,
    QueryBuilder,
    FormDataBuilder,
    UuidValidator,
} from './utilities';
import type {
    FileResponse,
    FileWithProject,
    FileWithMeeting,
    FileFilter,
    BulkFileOperation,
    BulkFileResponse,
    FileUploadData,
    FileMoveRequest,
    FileQueryParams,
} from '../../types/file.type';

/**
 * Upload a file
 */
export const uploadFile = async (
    fileData: FileUploadData
): Promise<FileResponse> => {
    const formData = FormDataBuilder.buildWithFile(
        fileData.file
    );

    // Backend expects project_id/meeting_id as query params (not form fields)
    const queryString = QueryBuilder.build({
        project_id: fileData.project_id,
        meeting_id: fileData.meeting_id,
    });

    return ApiWrapper.execute(() =>
        axiosInstance.post(`/files/upload${queryString}`, formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
        })
    );
};

/**
 * Get all files with filtering and pagination
 */
export const getFiles = async (
    filters?: FileFilter,
    params?: FileQueryParams
): Promise<{ data: FileResponse[]; pagination: any }> => {
    const queryParams = {
        ...filters,
        ...params,
    };

    const queryString = QueryBuilder.build(queryParams);

    return ApiWrapper.executePaginated(() =>
        axiosInstance.get(`/files${queryString}`)
    );
};

/**
 * Get a specific file by ID
 */
export const getFile = async (fileId: string): Promise<FileResponse> => {
    UuidValidator.validate(fileId, 'File ID');

    return ApiWrapper.execute(() =>
        axiosInstance.get(`/files/${fileId}`)
    );
};

/**
 * Update a file
 */
export const updateFile = async (
    fileId: string,
    updates: { filename?: string; file_type?: string }
): Promise<FileResponse> => {
    UuidValidator.validate(fileId, 'File ID');

    return ApiWrapper.execute(() =>
        axiosInstance.put(`/files/${fileId}`, updates)
    );
};

/**
 * Delete a file
 */
export const deleteFile = async (fileId: string): Promise<void> => {
    UuidValidator.validate(fileId, 'File ID');

    return ApiWrapper.executeVoid(() =>
        axiosInstance.delete(`/files/${fileId}`)
    );
};

/**
 * Bulk file operations (delete or move)
 */
export const bulkFileOperation = async (
    operation: BulkFileOperation
): Promise<BulkFileResponse> => {
    // Validate all file IDs
    operation.file_ids.forEach((id, index) => {
        UuidValidator.validate(id, `File ID at index ${index}`);
    });

    // Validate target IDs if moving
    if (operation.operation === 'move') {
        if (operation.target_project_id) {
            UuidValidator.validate(operation.target_project_id, 'Target Project ID');
        }
        if (operation.target_meeting_id) {
            UuidValidator.validate(operation.target_meeting_id, 'Target Meeting ID');
        }
    }

    return ApiWrapper.executeBulk(() =>
        axiosInstance.post('/files/bulk', operation)
    );
};

/**
 * Get files for a specific project
 */
export const getProjectFiles = async (
    projectId: string,
    params?: FileQueryParams
): Promise<{ data: FileWithProject[]; pagination: any }> => {
    UuidValidator.validate(projectId, 'Project ID');

    const queryParams = {
        ...params,
    };

    const queryString = QueryBuilder.build(queryParams);

    return ApiWrapper.executePaginated(() =>
        axiosInstance.get(`/projects/${projectId}/files${queryString}`)
    );
};

/**
 * Get files for a specific meeting
 */
export const getMeetingFiles = async (
    meetingId: string,
    params?: FileQueryParams
): Promise<{ data: FileWithMeeting[]; pagination: any }> => {
    UuidValidator.validate(meetingId, 'Meeting ID');

    const queryParams = {
        ...params,
    };

    const queryString = QueryBuilder.build(queryParams);

    return ApiWrapper.executePaginated(() =>
        axiosInstance.get(`/meetings/${meetingId}/files${queryString}`)
    );
};

/**
 * Get a file with project information
 */
export const getFileWithProject = async (
    fileId: string
): Promise<FileWithProject> => {
    UuidValidator.validate(fileId, 'File ID');

    return ApiWrapper.execute(() =>
        axiosInstance.get(`/files/${fileId}/with-project`)
    );
};

/**
 * Get a file with meeting information
 */
export const getFileWithMeeting = async (
    fileId: string
): Promise<FileWithMeeting> => {
    UuidValidator.validate(fileId, 'File ID');

    return ApiWrapper.execute(() =>
        axiosInstance.get(`/files/${fileId}/with-meeting`)
    );
};

/**
 * Move a file to a project or meeting
 */
export const moveFile = async (
    fileId: string,
    moveRequest: FileMoveRequest
): Promise<FileResponse> => {
    UuidValidator.validate(fileId, 'File ID');

    return ApiWrapper.execute(() =>
        axiosInstance.post(`/files/${fileId}/move`, moveRequest)
    );
};

// Convenience functions for common operations
export const deleteFiles = async (fileIds: string[]): Promise<BulkFileResponse> => {
    return bulkFileOperation({
        file_ids: fileIds,
        operation: 'delete',
    });
};

export const moveFilesToProject = async (
    fileIds: string[],
    projectId: string
): Promise<BulkFileResponse> => {
    UuidValidator.validate(projectId, 'Project ID');

    return bulkFileOperation({
        file_ids: fileIds,
        operation: 'move',
        target_project_id: projectId,
    });
};

export const moveFilesToMeeting = async (
    fileIds: string[],
    meetingId: string
): Promise<BulkFileResponse> => {
    UuidValidator.validate(meetingId, 'Meeting ID');

    return bulkFileOperation({
        file_ids: fileIds,
        operation: 'move',
        target_meeting_id: meetingId,
    });
};
