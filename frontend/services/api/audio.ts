// Audio File Management API
// Based on backend endpoints from app/api/endpoints/audio_file.py

import axiosInstance from './axiosInstance';
import { ApiWrapper, FormDataBuilder, QueryBuilder, UuidValidator } from './utilities';
import type {
    AudioFileResponse,
    AudioFileUpdate,
} from '../../types/audio_file.type';
import type { TranscriptResponse } from '../../types/transcript.type';

/**
 * Upload an audio file
 * Auto-creates a personal meeting if no meeting_id provided
 * Validates RBAC for existing meetings
 */
export const uploadAudioFile = async (
    file: File,
    meetingId?: string
): Promise<AudioFileResponse> => {
    if (meetingId) {
        UuidValidator.validate(meetingId, 'Meeting ID');
    }

    const queryParams = {
        meeting_id: meetingId,
    };

    const queryString = QueryBuilder.build(queryParams);

    const formData = FormDataBuilder.buildWithFile(file);

    return ApiWrapper.execute(() =>
        axiosInstance.post(`/audio-files/upload${queryString}`, formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
        })
    );
};

/**
 * Get a specific audio file by ID
 */
export const getAudioFile = async (audioId: string): Promise<AudioFileResponse> => {
    UuidValidator.validate(audioId, 'Audio File ID');

    return ApiWrapper.execute(() =>
        axiosInstance.get(`/audio-files/${audioId}`)
    );
};

/**
 * Get all audio files for a meeting
 */
export const getMeetingAudioFiles = async (
    meetingId: string
): Promise<AudioFileResponse[]> => {
    UuidValidator.validate(meetingId, 'Meeting ID');

    return ApiWrapper.executeList<AudioFileResponse>(() =>
        axiosInstance.get(`/meetings/${meetingId}/audio-files`)
    );
};

/**
 * Update audio file metadata
 */
export const updateAudioFile = async (
    audioId: string,
    updates: AudioFileUpdate
): Promise<AudioFileResponse> => {
    UuidValidator.validate(audioId, 'Audio File ID');

    return ApiWrapper.execute(() =>
        axiosInstance.put(`/audio-files/${audioId}`, updates)
    );
};

/**
 * Delete an audio file
 */
export const deleteAudioFile = async (audioId: string): Promise<void> => {
    UuidValidator.validate(audioId, 'Audio File ID');

    return ApiWrapper.executeVoid(() =>
        axiosInstance.delete(`/audio-files/${audioId}`)
    );
};

/**
 * Upload and transcribe audio (legacy combined operation)
 */
export const uploadAndTranscribeAudio = async (
    meetingId: string,
    file: File
): Promise<TranscriptResponse> => {
    try {
        const audioFile = await uploadAudioFile(file, meetingId);
        const transcriptResponse = await axiosInstance.post(
            `/transcripts/transcribe/${audioFile.id}`
        );
        return transcriptResponse.data.data;
    } catch (error) {
        console.error('Error uploading and transcribing audio:', error);
        throw error;
    }
};
