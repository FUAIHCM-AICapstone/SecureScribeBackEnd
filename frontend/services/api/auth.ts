
import axiosInstance from './axiosInstance';
import type {
  FirebaseLoginRequest,
  FirebaseLoginResponse,
  TokenRefreshRequest,
  TokenRefreshResponse,
  UserProfileResponse,
  UserUpdateRequest,
  UserUpdateResponse,
} from '../../types/auth.type';

const authApi = {
  /**
   * Firebase authentication with Google OAuth
   */
  firebaseLogin: async (data: FirebaseLoginRequest): Promise<FirebaseLoginResponse> => {
    const response = await axiosInstance.post('/auth/firebase/login', data);
    return response.data;
  },

  /**
   * Refresh access token
   */
  refreshToken: async (data: TokenRefreshRequest): Promise<TokenRefreshResponse> => {
    const response = await axiosInstance.post('/auth/refresh', data);
    return response.data;
  },

  /**
   * Get current user profile
   */
  getMe: async (): Promise<UserProfileResponse> => {
    const response = await axiosInstance.get('/me');
    return response.data;
  },

  /**
   * Update current user profile
   */
  updateMe: async (data: UserUpdateRequest): Promise<UserUpdateResponse> => {
    const response = await axiosInstance.put('/me', data);
    return response.data;
  },
};

export default authApi;
