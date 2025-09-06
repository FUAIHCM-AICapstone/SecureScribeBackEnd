// Common API Response (matches backend ApiResponse)
export interface ApiResponse<T> {
  success: boolean;
  message?: string;
  data?: T;
  errors?: string[];
}

// API Error Response
export interface ApiError {
  success: boolean;
  message: string;
  data?: any;
}

// Paginated Response (matches backend PaginatedResponse)
export interface PaginationMeta {
  page: number;
  limit: number;
  total: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
}

export interface PaginatedResponse<T> extends ApiResponse<T[]> {
  pagination?: PaginationMeta;
}

// Auth state for Redux store
export interface AuthState {
  isAuthenticated: boolean;
  isLoading: boolean;
  user: null | {
    id: string;
    email: string;
    name?: string;
    avatar_url?: string;
    bio?: string;
    position?: string;
    created_at: string;
    updated_at?: string;
  };
  error: string | null;
}

// Query parameters for API calls
export interface QueryParams {
  page?: number;
  limit?: number;
  order_by?: string;
  dir?: 'asc' | 'desc';
  search?: string;
}

// Generic filter interface
export interface BaseFilter {
  created_at_gte?: string;
  created_at_lte?: string;
  updated_at_gte?: string;
  updated_at_lte?: string;
}

// Bulk operation response
export interface BulkOperationResult {
  success: boolean;
  id?: string;
  error?: string;
}

export interface BulkResponse {
  success: boolean;
  message: string;
  data: BulkOperationResult[];
  total_processed: number;
  total_success: number;
  total_failed: number;
}

// Generic ID type for UUID validation
export type UUID = string;

// File upload types
export interface FileUploadData {
  file: File;
  [key: string]: any;
}

// WebSocket message types
export interface WebSocketMessage<T = any> {
  type: string;
  data: T;
  timestamp?: string;
}

// Device/FCM types
export interface DeviceInfo {
  device_name: string;
  device_type?: string;
  fcm_token?: string;
  last_active_at?: string;
  is_active?: boolean;
}

// Status types
export type StatusType = 'active' | 'inactive' | 'pending' | 'completed' | 'cancelled' | 'archived';
export type RoleType = 'admin' | 'owner' | 'member' | 'viewer';

// Generic response wrapper for consistency
export interface ApiResult<T> {
  data: T;
  error?: ApiError;
  loading?: boolean;
}