export interface GoogleCalendarConnectResponse {
    auth_url: string;
    state: string;
}

export interface GoogleCalendarEvent {
    id?: string;
    summary?: string;
    description?: string;
    start?: {
        dateTime?: string;
        date?: string;
    };
    end?: {
        dateTime?: string;
        date?: string;
    };
    location?: string;
    status?: string;
    created?: string;
    updated?: string;
}

export interface GoogleCalendarCallbackRequest {
    code: string;
}

export interface GoogleCalendarIntegrationStatus {
    connected: boolean;
    lastSync?: string;
    error?: string;
}

