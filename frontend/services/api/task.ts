// Task Management API
// Based on backend endpoints from app/api/endpoints/task.py

import axiosInstance from './axiosInstance';
import { ApiWrapper, QueryBuilder, UuidValidator } from './utilities';
import type {
    TaskCreate,
    TaskUpdate,
    TaskResponse,
    TaskFilter,
    TaskQueryParams,
    BulkTaskCreate,
    BulkTaskUpdate,
    BulkTaskResponse,
} from '../../types/task.type';

// Helpers for date conversion if needed by callers
export const toIsoUtc = (value?: string): string | undefined => {
    if (!value) return undefined;
    const d = new Date(value);
    if (Number.isNaN(d.getTime())) return undefined;
    return d.toISOString();
};

export const createTask = async (
    taskData: TaskCreate
): Promise<TaskResponse> => {
    return ApiWrapper.execute(() =>
        axiosInstance.post('/tasks', taskData)
    );
};

export const getTasks = async (
    filters?: TaskFilter,
    params?: TaskQueryParams
): Promise<{ data: TaskResponse[]; pagination: any }> => {
    const queryParams = {
        ...filters,
        ...params,
    };

    const queryString = QueryBuilder.build(queryParams);

    return ApiWrapper.executePaginated(() =>
        axiosInstance.get(`/tasks${queryString}`)
    );
};

export const getTask = async (taskId: string): Promise<TaskResponse> => {
    UuidValidator.validate(taskId, 'Task ID');
    return ApiWrapper.execute(() =>
        axiosInstance.get(`/tasks/${taskId}`)
    );
};

export const updateTask = async (
    taskId: string,
    updates: TaskUpdate
): Promise<TaskResponse> => {
    UuidValidator.validate(taskId, 'Task ID');
    return ApiWrapper.execute(() =>
        axiosInstance.put(`/tasks/${taskId}`, updates)
    );
};

export const deleteTask = async (taskId: string): Promise<void> => {
    UuidValidator.validate(taskId, 'Task ID');
    return ApiWrapper.executeVoid(() =>
        axiosInstance.delete(`/tasks/${taskId}`)
    );
};

export const bulkCreateTasks = async (
    payload: BulkTaskCreate
): Promise<BulkTaskResponse> => {
    return ApiWrapper.executeBulk(() =>
        axiosInstance.post('/tasks/bulk', payload)
    );
};

export const bulkUpdateTasks = async (
    payload: BulkTaskUpdate
): Promise<BulkTaskResponse> => {
    return ApiWrapper.executeBulk(() =>
        axiosInstance.put('/tasks/bulk', payload)
    );
};

export const bulkDeleteTasks = async (
    taskIds: string[]
): Promise<BulkTaskResponse> => {
    // Validate all task IDs
    taskIds.forEach((id, index) => {
        UuidValidator.validate(id, `Task ID at index ${index}`);
    });

    // Send JSON body per backend contract
    return ApiWrapper.executeBulk(() =>
        axiosInstance.delete(`/tasks/bulk`, { data: { task_ids: taskIds } })
    );
};


