import axiosInstance from './axiosInstance';
import type { User, UserUpdate } from '../../types/user.type';
import type { ApiResponse } from '../../types/common.type';

const userApi = {
  /**
   * Get current user profile
   */
  getMe: async (): Promise<ApiResponse<User>> => {
    const response = await axiosInstance.get('/me');
    return response.data;
  },

  /**
   * Update current user profile
   */
  updateMe: async (data: UserUpdate): Promise<ApiResponse<User>> => {
    const response = await axiosInstance.put('/me', data);
    return response.data;
  },
};

export default userApi;