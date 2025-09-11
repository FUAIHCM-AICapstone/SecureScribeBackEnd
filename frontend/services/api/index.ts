// API Services Index
// Centralized exports for all API functions and utilities

// Core utilities
export * from './utilities';
export * from './axiosInstance';

// Auth API
export * from './auth';

// File API
export * from './file';

// Meeting API
export * from './meeting';

// Notification API
export * from './notification';

// Project API
export * from './project';

// User API - selective export to avoid conflicts
export {
    getUsers,
    createUser,
    updateUser,
    deleteUser,
    bulkCreateUsers,
    bulkUpdateUsers,
    bulkDeleteUsers,
    getMe,
    updateMe,
    getWebSocketStatus as getUserWebSocketStatus,
    testStreamProgress as testUserStreamProgress,
    updateFCMToken as updateUserFCMToken
} from './user';

// Search API
export * from './search';

// Legacy exports for backward compatibility
export { default as authApi } from './auth';
export { default as userApi } from './user';
export { default as searchApi } from './search';
