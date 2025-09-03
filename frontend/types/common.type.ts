// Common API Response (matches backend ApiResponse)
export interface ApiResponse<T> {
  success: boolean;
  message?: string;
  data?: T;
}

// API Error Response
export interface ApiError {
  success: boolean;
  message: string;
  data?: any;
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