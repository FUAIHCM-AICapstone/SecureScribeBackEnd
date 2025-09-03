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