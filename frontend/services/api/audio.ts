import axiosInstance from './axiosInstance';
import type { TranscriptResponse } from '../../types/transcript.type';

export const uploadAndTranscribeAudio = async (
    meetingId: string,
    file: File
): Promise<TranscriptResponse> => {
    try {
        const formData = new FormData();
        formData.append('file', file);

        const uploadResponse = await axiosInstance.post(
            `/audio-files/upload?meeting_id=${meetingId}`,
            formData,
            {
                headers: {
                    'Content-Type': 'multipart/form-data',
                },
            }
        );

        const audioId = uploadResponse.data.data.id;

        const transcriptResponse = await axiosInstance.post(
            `/transcripts/transcribe/${audioId}`
        );

        return transcriptResponse.data.data;
    } catch (error) {
        console.error('Error uploading and transcribing audio:', error);
        throw error;
    }
};
