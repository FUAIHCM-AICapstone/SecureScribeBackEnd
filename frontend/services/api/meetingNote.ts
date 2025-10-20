import axiosInstance from './axiosInstance';
import { ApiWrapper, UuidValidator } from './utilities';
import type {
    MeetingNoteResponse,
    MeetingNoteRequest,
    MeetingNoteSummaryResponse,
} from '../../types/meeting.type';

export const createMeetingNote = async (
    meetingId: string
): Promise<MeetingNoteSummaryResponse> => {
    UuidValidator.validate(meetingId, 'Meeting ID');
    return ApiWrapper.execute(() =>
        axiosInstance.post(`/meetings/${meetingId}/notes`)
    );
};

export const getMeetingNote = async (
    meetingId: string
): Promise<MeetingNoteResponse> => {
    UuidValidator.validate(meetingId, 'Meeting ID');
    return ApiWrapper.execute(() =>
        axiosInstance.get(`/meetings/${meetingId}/notes`)
    );
};

export const updateMeetingNote = async (
    meetingId: string,
    payload: MeetingNoteRequest
): Promise<MeetingNoteResponse> => {
    UuidValidator.validate(meetingId, 'Meeting ID');
    return ApiWrapper.execute(() =>
        axiosInstance.put(`/meetings/${meetingId}/notes`, payload)
    );
};

export const deleteMeetingNote = async (
    meetingId: string
): Promise<void> => {
    UuidValidator.validate(meetingId, 'Meeting ID');
    return ApiWrapper.execute(() =>
        axiosInstance.delete(`/meetings/${meetingId}/notes`)
    );
};
