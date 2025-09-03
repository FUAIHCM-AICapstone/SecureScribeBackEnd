
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
   * Set authorization token for future requests
   */
  setToken: (token: string): void => {
    axiosInstance.defaults.headers.common['Authorization'] = `Bearer ${token}`;
  },

  /**
   * Clear authorization token
   */
  clearToken: (): void => {
    delete axiosInstance.defaults.headers.common['Authorization'];
  },

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

  /**
   * Logout user (client-side only, remove tokens)
   */
  logout: async (): Promise<any> => {
    // Client-side logout - just return success
    // Backend logout can be handled if needed
    return Promise.resolve({ success: true, message: 'Logged out successfully' });
  },
};

export default authApi;
