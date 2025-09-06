// Notification Management API
// Based on backend endpoints from app/api/endpoints/notificaiton.py

import axiosInstance from './axiosInstance';
import { ApiWrapper, QueryBuilder, UuidValidator } from './utilities';
import type {
    NotificationCreate,
    NotificationGlobalCreate,
    NotificationResponse,
    NotificationUpdate,
    NotificationQueryParams,
    DeviceFCMUpdate,
    WebSocketConnectionStatus,
} from '../../types/notification.type';

/**
 * Get notifications with pagination
 */
export const getNotifications = async (
    params?: NotificationQueryParams
): Promise<{ data: NotificationResponse[]; pagination: any }> => {
    const queryParams = {
        ...params,
    };

    const queryString = QueryBuilder.build(queryParams);

    return ApiWrapper.executePaginated(() =>
        axiosInstance.get(`/notifications${queryString}`)
    );
};

/**
 * Get a specific notification by ID
 */
export const getNotification = async (
    notificationId: string
): Promise<NotificationResponse> => {
    UuidValidator.validate(notificationId, 'Notification ID');

    return ApiWrapper.execute(() =>
        axiosInstance.get(`/notifications/${notificationId}`)
    );
};

/**
 * Send notifications to specific users
 */
export const sendNotifications = async (
    notificationData: NotificationCreate
): Promise<NotificationResponse[]> => {
    // Validate user IDs
    notificationData.user_ids.forEach((id, index) => {
        UuidValidator.validate(id, `User ID at index ${index}`);
    });

    return ApiWrapper.executeList(() =>
        axiosInstance.post('/notifications/send', notificationData)
    );
};

/**
 * Send global notification to all users
 */
export const sendGlobalNotification = async (
    notificationData: NotificationGlobalCreate
): Promise<NotificationResponse[]> => {
    return ApiWrapper.executeList(() =>
        axiosInstance.post('/notifications/send-global', notificationData)
    );
};

/**
 * Mark notification as read/unread
 */
export const updateNotification = async (
    notificationId: string,
    updates: NotificationUpdate
): Promise<NotificationResponse> => {
    UuidValidator.validate(notificationId, 'Notification ID');

    return ApiWrapper.execute(() =>
        axiosInstance.patch(`/notifications/${notificationId}/read`, updates)
    );
};

/**
 * Delete a notification
 */
export const deleteNotification = async (
    notificationId: string
): Promise<void> => {
    UuidValidator.validate(notificationId, 'Notification ID');

    return ApiWrapper.executeVoid(() =>
        axiosInstance.delete(`/notifications/${notificationId}`)
    );
};

/**
 * Update FCM token for device
 */
export const updateFCMToken = async (
    fcmData: DeviceFCMUpdate
): Promise<{ device_id: string }> => {
    return ApiWrapper.execute(() =>
        axiosInstance.post('/users/me/devices/fcm-token', fcmData)
    );
};

/**
 * Get WebSocket connection status
 */
export const getWebSocketStatus = async (): Promise<WebSocketConnectionStatus> => {
    return ApiWrapper.execute(() =>
        axiosInstance.get('/users/me/websocket-status')
    );
};

/**
 * Test stream progress (for development/testing)
 */
export const testStreamProgress = async (): Promise<{
    task_id: string;
    user_id: string;
    status: string;
}> => {
    return ApiWrapper.execute(() =>
        axiosInstance.post('/users/me/test-stream')
    );
};

// Convenience functions for common operations
export const markNotificationAsRead = async (
    notificationId: string
): Promise<NotificationResponse> => {
    return updateNotification(notificationId, { is_read: true });
};

export const markNotificationAsUnread = async (
    notificationId: string
): Promise<NotificationResponse> => {
    return updateNotification(notificationId, { is_read: false });
};

export const getUnreadNotifications = async (
    params?: Omit<NotificationQueryParams, 'is_read'>
): Promise<{ data: NotificationResponse[]; pagination: any }> => {
    return getNotifications({ ...params, is_read: false });
};

export const getReadNotifications = async (
    params?: Omit<NotificationQueryParams, 'is_read'>
): Promise<{ data: NotificationResponse[]; pagination: any }> => {
    return getNotifications({ ...params, is_read: true });
};

// WebSocket URL builder
export const getWebSocketUrl = (token?: string): string => {
    const baseUrl = (globalThis as any).process?.env?.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';
    const apiVersion = 'v1';
    const wsProtocol = baseUrl.startsWith('https') ? 'wss' : 'ws';
    const wsBase = baseUrl.replace(/^https?/, wsProtocol);

    let url = `${wsBase}/api/${apiVersion}/notifications/ws`;

    if (token) {
        url += `?authorization=Bearer%20${encodeURIComponent(token)}`;
    }

    return url;
};
