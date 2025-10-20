import axiosInstance from './axiosInstance';
import { ApiWrapper, UuidValidator } from './utilities';
import type {
    TranscriptResponse,
    TranscriptCreate,
    TranscriptUpdate,
    TranscriptsPaginatedResponse,
} from '../../types/transcript.type';

export const getTranscriptsByMeeting = async (
    meetingId: string
): Promise<TranscriptResponse[]> => {
    UuidValidator.validate(meetingId, 'Meeting ID');
    const response = await ApiWrapper.execute<TranscriptsPaginatedResponse>(() =>
        axiosInstance.get(`/transcripts?meeting_id=${meetingId}&limit=100`)
    );
    return response.data || [];
};

export const getTranscript = async (
    transcriptId: string
): Promise<TranscriptResponse> => {
    UuidValidator.validate(transcriptId, 'Transcript ID');
    return ApiWrapper.execute(() =>
        axiosInstance.get(`/transcripts/${transcriptId}`)
    );
};

export const createTranscript = async (
    payload: TranscriptCreate
): Promise<TranscriptResponse> => {
    return ApiWrapper.execute(() =>
        axiosInstance.post('/transcripts', payload)
    );
};

export const updateTranscript = async (
    transcriptId: string,
    payload: TranscriptUpdate
): Promise<TranscriptResponse> => {
    UuidValidator.validate(transcriptId, 'Transcript ID');
    return ApiWrapper.execute(() =>
        axiosInstance.put(`/transcripts/${transcriptId}`, payload)
    );
};

export const deleteTranscript = async (
    transcriptId: string
): Promise<void> => {
    UuidValidator.validate(transcriptId, 'Transcript ID');
    return ApiWrapper.execute(() =>
        axiosInstance.delete(`/transcripts/${transcriptId}`)
    );
};

export const transcribeAudio = async (
    audioId: string
): Promise<TranscriptResponse> => {
    UuidValidator.validate(audioId, 'Audio ID');
    return ApiWrapper.execute(() =>
        axiosInstance.post(`/transcripts/transcribe/${audioId}`)
    );
};
