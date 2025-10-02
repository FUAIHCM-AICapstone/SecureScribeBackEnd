import axiosInstance from './axiosInstance';
import {
    GoogleCalendarConnectResponse,
    GoogleCalendarEvent,
    GoogleCalendarIntegrationStatus
} from '../../types/googleCalendar.type';

export const connectGoogleCalendar = async (): Promise<GoogleCalendarConnectResponse> => {
    const response = await axiosInstance.get('/auth/google/connect');
    return response.data.data;
};

export const handleGoogleCalendarCallback = async (code: string): Promise<{ success: boolean; message: string }> => {
    const response = await axiosInstance.get(`/auth/google/callback?code=${encodeURIComponent(code)}`);
    return response.data.data;
};

export const getGoogleCalendarEvents = async (): Promise<GoogleCalendarEvent[]> => {
    const response = await axiosInstance.get('/calendar/events');
    return response.data.data;
};

export const getGoogleCalendarIntegrationStatus = async (): Promise<GoogleCalendarIntegrationStatus> => {
    try {
        await getGoogleCalendarEvents();
        return { connected: true, lastSync: new Date().toISOString() };
    } catch {
        return { connected: false, error: 'Google Calendar not connected' };
    }
};
