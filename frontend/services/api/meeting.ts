// Meeting Management API
// Based on backend endpoints from app/api/endpoints/meeting.py

import axiosInstance from './axiosInstance';
import { ApiWrapper, QueryBuilder, UuidValidator } from './utilities';
import type {
    MeetingCreate,
    MeetingResponse,
    MeetingUpdate,
    MeetingFilter,
    MeetingQueryParams,
    MeetingWithProjects,
} from '../../types/meeting.type';

/**
 * Create a new meeting
 */
export const createMeeting = async (
    meetingData: MeetingCreate
): Promise<MeetingResponse> => {
    return ApiWrapper.execute(() =>
        axiosInstance.post('/meetings', meetingData)
    );
};

/**
 * Get all meetings with filtering and pagination
 */
export const getMeetings = async (
    filters?: MeetingFilter,
    params?: MeetingQueryParams
): Promise<{ data: MeetingResponse[]; pagination: any }> => {
    const queryParams = {
        ...filters,
        ...params,
    };

    const queryString = QueryBuilder.build(queryParams);

    return ApiWrapper.executePaginated(() =>
        axiosInstance.get(`/meetings${queryString}`)
    );
};

/**
 * Get a specific meeting by ID
 */
export const getMeeting = async (meetingId: string): Promise<MeetingWithProjects> => {
    UuidValidator.validate(meetingId, 'Meeting ID');

    return ApiWrapper.execute(() =>
        axiosInstance.get(`/meetings/${meetingId}`)
    );
};

/**
 * Update a meeting
 */
export const updateMeeting = async (
    meetingId: string,
    updates: MeetingUpdate
): Promise<MeetingResponse> => {
    UuidValidator.validate(meetingId, 'Meeting ID');

    return ApiWrapper.execute(() =>
        axiosInstance.put(`/meetings/${meetingId}`, updates)
    );
};

/**
 * Delete a meeting
 */
export const deleteMeeting = async (meetingId: string): Promise<void> => {
    UuidValidator.validate(meetingId, 'Meeting ID');

    return ApiWrapper.executeVoid(() =>
        axiosInstance.delete(`/meetings/${meetingId}`)
    );
};

/**
 * Add a meeting to a project
 */
export const addMeetingToProject = async (
    projectId: string,
    meetingId: string
): Promise<void> => {
    UuidValidator.validate(projectId, 'Project ID');
    UuidValidator.validate(meetingId, 'Meeting ID');

    return ApiWrapper.executeVoid(() =>
        axiosInstance.post(`/projects/${projectId}/meetings/${meetingId}`)
    );
};

/**
 * Remove a meeting from a project
 */
export const removeMeetingFromProject = async (
    projectId: string,
    meetingId: string
): Promise<void> => {
    UuidValidator.validate(projectId, 'Project ID');
    UuidValidator.validate(meetingId, 'Meeting ID');

    return ApiWrapper.executeVoid(() =>
        axiosInstance.delete(`/projects/${projectId}/meetings/${meetingId}`)
    );
};

// Convenience functions for common queries
export const getPersonalMeetings = async (
    params?: Omit<MeetingQueryParams, 'is_personal'>
): Promise<{ data: MeetingResponse[]; pagination: any }> => {
    return getMeetings({ is_personal: true }, params);
};

export const getProjectMeetings = async (
    projectId: string,
    params?: MeetingQueryParams
): Promise<{ data: MeetingResponse[]; pagination: any }> => {
    UuidValidator.validate(projectId, 'Project ID');

    return getMeetings({ project_id: projectId }, params);
};

export const getActiveMeetings = async (
    params?: Omit<MeetingQueryParams, 'status'>
): Promise<{ data: MeetingResponse[]; pagination: any }> => {
    return getMeetings({ status: 'active' }, params);
};

export const getCompletedMeetings = async (
    params?: Omit<MeetingQueryParams, 'status'>
): Promise<{ data: MeetingResponse[]; pagination: any }> => {
    return getMeetings({ status: 'completed' }, params);
};

export const getCancelledMeetings = async (
    params?: Omit<MeetingQueryParams, 'status'>
): Promise<{ data: MeetingResponse[]; pagination: any }> => {
    return getMeetings({ status: 'cancelled' }, params);
};

// Meeting status management
export const completeMeeting = async (meetingId: string): Promise<MeetingResponse> => {
    return updateMeeting(meetingId, { status: 'completed' });
};

export const cancelMeeting = async (meetingId: string): Promise<MeetingResponse> => {
    return updateMeeting(meetingId, { status: 'cancelled' });
};

export const activateMeeting = async (meetingId: string): Promise<MeetingResponse> => {
    return updateMeeting(meetingId, { status: 'active' });
};
