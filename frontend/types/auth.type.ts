// Firebase Authentication Types
export interface FirebaseLoginRequest {
  id_token: string;
}

export interface TokenRefreshRequest {
  refresh_token: string;
}

// User Profile Types
export interface UserProfile {
  id: string;
  email: string;
  name?: string;
  avatar_url?: string;
  bio?: string;
  position?: string;
  created_at: string;
  updated_at?: string;
}

// Token Response
export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

// Auth Response
export interface AuthResponse {
  user: UserProfile;
  token: TokenResponse;
}

// User Update Request
export interface UserUpdateRequest {
  name?: string;
  bio?: string;
  position?: string;
  avatar_url?: string;
}

// Signup Request
export interface SignupRequest {
  email: string;
  password: string;
  confirm_password: string;
  device_address: string;
  role?: string;
}

// Login Response
export interface MeResponse {
  id: string;
  email: string;
  name?: string;
  avatar_url?: string;
  bio?: string;
  position?: string;
  created_at: string;
  updated_at?: string;
}

// Common API Response (matches backend ApiResponse)
export interface ApiResponse<T> {
  success: boolean;
  message?: string;
  data?: T;
}

// Specific Response Types
export type FirebaseLoginResponse = ApiResponse<AuthResponse>;
export type TokenRefreshResponse = ApiResponse<TokenResponse>;
export type UserProfileResponse = ApiResponse<UserProfile>;
export type UserUpdateResponse = ApiResponse<UserProfile>;
export type SignupResponseModel = ApiResponse<UserProfile>;
