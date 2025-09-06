// Notification Management Types
// Based on backend schemas from app/schemas/notification.py

export interface NotificationBase {
    type?: string;
    payload?: Record<string, any>;
    channel?: string;
}

export interface NotificationCreate extends NotificationBase {
    user_ids: string[];
}

export type NotificationGlobalCreate = NotificationBase;

export interface NotificationResponse extends NotificationBase {
    id: string;
    user_id: string;
    is_read: boolean;
    created_at: string;
    updated_at?: string;
}

export interface NotificationUpdate {
    is_read?: boolean;
}

export interface NotificationStreamEvent {
    type: string;
    data: Record<string, any>;
    timestamp: string;
}

// WebSocket related types
export interface WebSocketMessage {
    type: string;
    data: Record<string, any>;
}

export interface WebSocketConnectionStatus {
    user_id: string;
    is_connected: boolean;
    user_connections: number;
    total_active_connections: number;
    total_unique_users: number;
    metrics: {
        total_connections_ever: number;
        messages_sent: number;
        messages_received: number;
        redis_errors: number;
        websocket_errors: number;
    };
}

// FCM Token update
export interface DeviceFCMUpdate {
    device_name: string;
    fcm_token: string;
    device_type?: string;
}

// Query parameters
export interface NotificationQueryParams {
    page?: number;
    limit?: number;
    order_by?: string;
    dir?: 'asc' | 'desc';
    is_read?: boolean;
}

// API Response Types
export type NotificationsPaginatedResponse = PaginatedResponse<NotificationResponse>;
export type NotificationApiResponse = ApiResponse<NotificationResponse>;

// Import common types
import type { ApiResponse, PaginatedResponse } from './common.type';
