// Transcript Management API
// Based on backend endpoints from app/api/endpoints/transcript.py

import axiosInstance from './axiosInstance';
import { ApiWrapper, QueryBuilder, UuidValidator } from './utilities';
import type {
    TranscriptResponse,
    TranscriptCreate,
    TranscriptUpdate,
    TranscriptFilter,
    TranscriptQueryParams,
    BulkTranscriptCreate,
    BulkTranscriptUpdate,
    BulkTranscriptDelete,
    BulkTranscriptResponse,
} from '../../types/transcript.type';

/**
 * Transcribe an audio file
 */
export const transcribeAudio = async (
    audioId: string
): Promise<TranscriptResponse> => {
    UuidValidator.validate(audioId, 'Audio ID');
    return ApiWrapper.execute(() =>
        axiosInstance.post(`/transcripts/transcribe/${audioId}`)
    );
};

/**
 * Get all transcripts with filtering and pagination
 */
export const getTranscripts = async (
    filters?: TranscriptFilter,
    params?: TranscriptQueryParams
): Promise<{ data: TranscriptResponse[]; pagination: any }> => {
    const queryParams = {
        ...filters,
        ...params,
    };

    const queryString = QueryBuilder.build(queryParams);

    return ApiWrapper.executePaginated(() =>
        axiosInstance.get(`/transcripts${queryString}`)
    );
};

/**
 * Get a specific transcript by ID
 */
export const getTranscript = async (
    transcriptId: string
): Promise<TranscriptResponse> => {
    UuidValidator.validate(transcriptId, 'Transcript ID');
    return ApiWrapper.execute(() =>
        axiosInstance.get(`/transcripts/${transcriptId}`)
    );
};

/**
 * Get transcripts for a specific meeting
 */
export const getTranscriptsByMeeting = async (
    meetingId: string
): Promise<TranscriptResponse[]> => {
    UuidValidator.validate(meetingId, 'Meeting ID');
    return ApiWrapper.executeList<TranscriptResponse>(() =>
        axiosInstance.get(`/transcripts?meeting_id=${meetingId}&limit=100`)
    );
};

/**
 * Get transcript by meeting ID (single result)
 */
export const getMeetingTranscript = async (
    meetingId: string
): Promise<TranscriptResponse> => {
    UuidValidator.validate(meetingId, 'Meeting ID');
    return ApiWrapper.execute(() =>
        axiosInstance.get(`/transcripts/meeting/${meetingId}`)
    );
};

/**
 * Create a new transcript
 */
export const createTranscript = async (
    payload: TranscriptCreate
): Promise<TranscriptResponse> => {
    return ApiWrapper.execute(() =>
        axiosInstance.post('/transcripts', payload)
    );
};

/**
 * Update a transcript
 */
export const updateTranscript = async (
    transcriptId: string,
    payload: TranscriptUpdate
): Promise<TranscriptResponse> => {
    UuidValidator.validate(transcriptId, 'Transcript ID');
    return ApiWrapper.execute(() =>
        axiosInstance.put(`/transcripts/${transcriptId}`, payload)
    );
};

/**
 * Delete a transcript
 */
export const deleteTranscript = async (
    transcriptId: string
): Promise<void> => {
    UuidValidator.validate(transcriptId, 'Transcript ID');
    return ApiWrapper.executeVoid(() =>
        axiosInstance.delete(`/transcripts/${transcriptId}`)
    );
};

/**
 * Bulk create transcripts
 */
export const bulkCreateTranscripts = async (
    payload: BulkTranscriptCreate
): Promise<BulkTranscriptResponse> => {
    return ApiWrapper.executeBulk(() =>
        axiosInstance.post('/transcripts/bulk', payload)
    );
};

/**
 * Bulk update transcripts
 */
export const bulkUpdateTranscripts = async (
    payload: BulkTranscriptUpdate
): Promise<BulkTranscriptResponse> => {
    return ApiWrapper.executeBulk(() =>
        axiosInstance.put('/transcripts/bulk', payload)
    );
};

/**
 * Bulk delete transcripts
 */
export const bulkDeleteTranscripts = async (
    payload: BulkTranscriptDelete
): Promise<BulkTranscriptResponse> => {
    return ApiWrapper.executeBulk(() =>
        axiosInstance.delete('/transcripts/bulk', { data: payload })
    );
};
