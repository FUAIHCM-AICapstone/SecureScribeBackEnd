// User Management API
// Based on backend endpoints from app/api/endpoints/user.py

import axiosInstance from './axiosInstance';
import { ApiWrapper, QueryBuilder, UuidValidator } from './utilities';
import type { User, UserUpdate, UserCreate, BulkUserCreate, BulkUserUpdate } from '../../types/user.type';
import type { DeviceFCMUpdate } from '../../types/notification.type';

/**
 * Get all users with pagination and filtering
 */
export const getUsers = async (params?: {
  page?: number;
  limit?: number;
  order_by?: string;
  dir?: string;
  name?: string;
  email?: string;
  position?: string;
  created_at_gte?: string;
  created_at_lte?: string;
}): Promise<{ data: User[]; pagination: any }> => {
  const queryString = QueryBuilder.build(params || {});

  return ApiWrapper.executePaginated(() =>
    axiosInstance.get(`/users${queryString}`)
  );
};

/**
 * Create a new user
 */
export const createUser = async (userData: UserCreate): Promise<User> => {
  return ApiWrapper.execute(() =>
    axiosInstance.post('/users', userData)
  );
};

/**
 * Update a user
 */
export const updateUser = async (
  userId: string,
  updates: UserUpdate
): Promise<User> => {
  UuidValidator.validate(userId, 'User ID');

  return ApiWrapper.execute(() =>
    axiosInstance.put(`/users/${userId}`, updates)
  );
};

/**
 * Delete a user
 */
export const deleteUser = async (userId: string): Promise<void> => {
  UuidValidator.validate(userId, 'User ID');

  return ApiWrapper.executeVoid(() =>
    axiosInstance.delete(`/users/${userId}`)
  );
};

/**
 * Bulk create users
 */
export const bulkCreateUsers = async (
  bulkData: BulkUserCreate
): Promise<any[]> => {
  return ApiWrapper.executeList(() =>
    axiosInstance.post('/users/bulk', bulkData)
  );
};

/**
 * Bulk update users
 */
export const bulkUpdateUsers = async (
  bulkData: BulkUserUpdate
): Promise<any[]> => {
  return ApiWrapper.executeList(() =>
    axiosInstance.put('/users/bulk', bulkData)
  );
};

/**
 * Bulk delete users
 */
export const bulkDeleteUsers = async (userIds: string[]): Promise<any> => {
  // Validate all user IDs
  userIds.forEach((id, index) => {
    UuidValidator.validate(id, `User ID at index ${index}`);
  });

  const queryString = QueryBuilder.build({
    user_ids: userIds.join(','),
  });

  return ApiWrapper.executeBulk(() =>
    axiosInstance.delete(`/users/bulk${queryString}`)
  );
};

/**
 * Get current user profile
 */
export const getMe = async (): Promise<User> => {
  return ApiWrapper.execute(() =>
    axiosInstance.get('/me')
  );
};

/**
 * Update current user profile
 */
export const updateMe = async (updates: UserUpdate): Promise<User> => {
  return ApiWrapper.execute(() =>
    axiosInstance.put('/me', updates)
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

/**
 * Get WebSocket connection status
 */
export const getWebSocketStatus = async (): Promise<any> => {
  return ApiWrapper.execute(() =>
    axiosInstance.get('/users/me/websocket-status')
  );
};

// Legacy export for backward compatibility
const userApi = {
  getMe: async (): Promise<any> => {
    const user = await getMe();
    return { success: true, data: user };
  },

  updateMe: async (data: UserUpdate): Promise<any> => {
    const user = await updateMe(data);
    return { success: true, data: user };
  },
};

export default userApi;