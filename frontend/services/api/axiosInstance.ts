import axios, { InternalAxiosRequestConfig, AxiosResponse, AxiosError } from 'axios';
import Cookies from 'js-cookie';
import authApi from './auth';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api';
const API_VERSION = 'v1';

// Flag to prevent multiple refresh attempts
let isRefreshing = false;
let failedQueue: Array<{
    resolve: (value?: any) => void;
    reject: (reason?: any) => void;
}> = [];

const processQueue = (error: any, token: string | null = null) => {
    failedQueue.forEach(({ resolve, reject }) => {
        if (error) {
            reject(error);
        } else {
            resolve(token);
        }
    });

    failedQueue = [];
};

const axiosInstance = axios.create({
    baseURL: `${API_BASE_URL}/${API_VERSION}`,
});

axiosInstance.interceptors.request.use(
    (config: InternalAxiosRequestConfig) => {
        const token = Cookies.get('access_token');
        const refreshToken = Cookies.get('refresh_token');
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
            config.headers["Access-Control-Allow-Origin"] = "*";
            if (refreshToken) {
                config.headers["x-refresh-token"] = refreshToken;
            }
        }
        return config;
    },
    (error) => Promise.reject(error)
);

axiosInstance.interceptors.response.use(
    (response: AxiosResponse) => response,
    async (error: AxiosError) => {
        // If backend returns insufficient fish balance, set a short-lived cookie
        try {
            const respData: any = error.response?.data;
            if (respData && typeof respData.message === 'string' && respData.message.includes('insufficient_fish_balance')) {
                // set a cookie that RootLayoutClient will read via URL param rewrite
                if (typeof window !== 'undefined') {
                    // store a flag locally so client layout can show modal immediately
                    window.localStorage.setItem('insufficient_fish_balance', '1');
                }
            }
        } catch {
            // ignore
        }
        const originalRequest = error.config as any;

        if (error.response?.status === 401 && !originalRequest._retry) {
            if (isRefreshing) {
                // If already refreshing, add to queue
                return new Promise((resolve, reject) => {
                    failedQueue.push({ resolve, reject });
                }).then(() => {
                    return axiosInstance(originalRequest);
                }).catch((err) => {
                    return Promise.reject(err);
                });
            }

            originalRequest._retry = true;
            isRefreshing = true;

            const refreshToken = Cookies.get('refresh_token');

            if (!refreshToken) {
                // No refresh token available, redirect to login
                processQueue(error, null);
                isRefreshing = false;

                // Clear cookies and redirect to auth page
                Cookies.remove('access_token');
                Cookies.remove('refresh_token');

                if (typeof window !== 'undefined') {
                    window.location.href = '/auth?toast=session_expired';
                }

                return Promise.reject(error);
            }

            try {
                // Attempt to refresh token
                const response = await authApi.refreshToken({
                    refresh_token: refreshToken!
                });

                if (response.success && response.data) {
                    const { access_token, refresh_token } = response.data;

                    if (!access_token) {
                        throw new Error('No access token received from refresh');
                    }

                    // Update cookies with new tokens
                    Cookies.set('access_token', access_token, { expires: 7 }); // 7 days
                    if (refresh_token) {
                        Cookies.set('refresh_token', refresh_token, { expires: 30 }); // 30 days
                    }

                    // Update axios default headers
                    axiosInstance.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;

                    // Process queued requests
                    processQueue(null, access_token);
                    isRefreshing = false;

                    // Retry the original request
                    originalRequest.headers['Authorization'] = `Bearer ${access_token}`;
                    return axiosInstance(originalRequest);
                } else {
                    throw new Error('Failed to refresh token');
                }
            } catch (refreshError) {
                console.error('Token refresh failed:', refreshError);

                // Clear cookies and redirect to login
                Cookies.remove('access_token');
                Cookies.remove('refresh_token');

                processQueue(refreshError, null);
                isRefreshing = false;

                if (typeof window !== 'undefined') {
                    window.location.href = '/auth?toast=session_expired';
                }

                return Promise.reject(refreshError);
            }
        }

        return Promise.reject(error);
    }
);
export { API_BASE_URL, API_VERSION };
export default axiosInstance;
