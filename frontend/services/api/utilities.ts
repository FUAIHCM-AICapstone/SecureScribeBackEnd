// API Utilities for error handling and response transformation
// Provides common patterns for API calls, error handling, and data transformation

import type { ApiResponse, ApiError } from '../../types/common.type';

// Type definitions for axios (avoiding direct import to prevent module resolution issues)
type AxiosError = any;
type AxiosResponse<T = any> = {
    data: T;
    status: number;
    statusText: string;
    headers: any;
    config: any;
};

/**
 * Generic API error handler
 */
export class ApiErrorHandler {
    static handle(error: AxiosError): ApiError {
        if (error.response) {
            // Server responded with error status
            const { status, data } = error.response;

            if (status === 400) {
                return {
                    success: false,
                    message: data?.message || 'Bad Request',
                    data: data?.data,
                };
            }

            if (status === 401) {
                return {
                    success: false,
                    message: data?.message || 'Unauthorized',
                    data: data?.data,
                };
            }

            if (status === 403) {
                return {
                    success: false,
                    message: data?.message || 'Forbidden',
                    data: data?.data,
                };
            }

            if (status === 404) {
                return {
                    success: false,
                    message: data?.message || 'Not Found',
                    data: data?.data,
                };
            }

            if (status === 422) {
                return {
                    success: false,
                    message: data?.message || 'Validation Error',
                    data: data?.data,
                };
            }

            if (status >= 500) {
                return {
                    success: false,
                    message: data?.message || 'Internal Server Error',
                    data: data?.data,
                };
            }

            return {
                success: false,
                message: data?.message || `HTTP ${status} Error`,
                data: data?.data,
            };
        }

        if (error.request) {
            // Request was made but no response received
            return {
                success: false,
                message: 'Network Error - No response received',
            };
        }

        // Something else happened
        return {
            success: false,
            message: error.message || 'Unknown Error',
        };
    }
}

/**
 * Generic response transformer
 */
export class ResponseTransformer {
    static transformSuccess<T>(response: AxiosResponse<ApiResponse<T>>): T {
        const { data } = response;

        if (!data.success) {
            throw new Error(data.message || 'API returned success: false');
        }

        if (!data.data) {
            throw new Error('API returned no data');
        }

        return data.data;
    }

    static transformList<T>(response: AxiosResponse<any>): T[] {
        const { data } = response;

        if (!data.success) {
            throw new Error(data.message || 'API returned success: false');
        }

        if (!data.data) {
            return [];
        }

        // Handle both direct array and paginated response
        if (Array.isArray(data.data)) {
            return data.data;
        }

        return [];
    }

    static transformPaginated(response: AxiosResponse<any>) {
        const { data } = response;

        if (!data.success) {
            throw new Error(data.message || 'API returned success: false');
        }

        return {
            data: data.data || [],
            pagination: data.pagination || {
                page: 1,
                limit: 20,
                total: 0,
                total_pages: 0,
                has_next: false,
                has_prev: false,
            },
        };
    }

    static transformBulk(response: AxiosResponse<any>) {
        const { data } = response;

        if (!data.success && data.total_failed > 0) {
            throw new Error(data.message || 'Bulk operation partially failed');
        }

        return {
            success: data.success,
            message: data.message,
            data: data.data || [],
            total_processed: data.total_processed || 0,
            total_success: data.total_success || 0,
            total_failed: data.total_failed || 0,
        };
    }
}

/**
 * Generic API wrapper with error handling
 */
export class ApiWrapper {
    static async execute<T>(
        apiCall: () => Promise<AxiosResponse<ApiResponse<T>>>
    ): Promise<T> {
        try {
            const response = await apiCall();
            return ResponseTransformer.transformSuccess(response);
        } catch (error) {
            throw ApiErrorHandler.handle(error as AxiosError);
        }
    }

    static async executeList<T>(
        apiCall: () => Promise<AxiosResponse<any>>
    ): Promise<T[]> {
        try {
            const response = await apiCall();
            return ResponseTransformer.transformList<T>(response);
        } catch (error) {
            throw ApiErrorHandler.handle(error as AxiosError);
        }
    }

    static async executePaginated<T>(
        apiCall: () => Promise<AxiosResponse<any>>
    ): Promise<{ data: T[]; pagination: any }> {
        try {
            const response = await apiCall();
            return ResponseTransformer.transformPaginated(response);
        } catch (error) {
            throw ApiErrorHandler.handle(error as AxiosError);
        }
    }

    static async executeBulk(
        apiCall: () => Promise<AxiosResponse<any>>
    ): Promise<{
        success: boolean;
        message: string;
        data: any[];
        total_processed: number;
        total_success: number;
        total_failed: number;
    }> {
        try {
            const response = await apiCall();
            return ResponseTransformer.transformBulk(response);
        } catch (error) {
            throw ApiErrorHandler.handle(error as AxiosError);
        }
    }

    static async executeVoid(
        apiCall: () => Promise<AxiosResponse<any>>
    ): Promise<void> {
        try {
            const response = await apiCall();
            if (!response.data.success) {
                throw new Error(response.data.message || 'API call failed');
            }
        } catch (error) {
            throw ApiErrorHandler.handle(error as AxiosError);
        }
    }
}

/**
 * Query parameter builder
 */
export class QueryBuilder {
    static build(params: Record<string, any>): string {
        const filtered = Object.entries(params)
            .filter(([, value]) => value !== undefined && value !== null && value !== '')
            .map(([key, value]) => {
                if (Array.isArray(value)) {
                    return `${key}=${value.join(',')}`;
                }
                return `${key}=${encodeURIComponent(String(value))}`;
            });

        return filtered.length > 0 ? `?${filtered.join('&')}` : '';
    }
}

/**
 * Form data builder for file uploads
 */
export class FormDataBuilder {
    static build(data: Record<string, any>): FormData {
        const formData = new FormData();

        Object.entries(data).forEach(([key, value]) => {
            if (value !== undefined && value !== null) {
                if (Array.isArray(value)) {
                    formData.append(key, value.join(','));
                } else {
                    formData.append(key, String(value));
                }
            }
        });

        return formData;
    }

    static buildWithFile(file: File, additionalData?: Record<string, any>): FormData {
        const formData = new FormData();
        formData.append('file', file);

        if (additionalData) {
            Object.entries(additionalData).forEach(([key, value]) => {
                if (value !== undefined && value !== null) {
                    if (Array.isArray(value)) {
                        formData.append(key, value.join(','));
                    } else {
                        formData.append(key, String(value));
                    }
                }
            });
        }

        return formData;
    }
}

/**
 * UUID validation utility
 */
export class UuidValidator {
    static isValid(uuid: string): boolean {
        const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
        return uuidRegex.test(uuid);
    }

    static validate(uuid: string, fieldName: string = 'ID'): void {
        if (!this.isValid(uuid)) {
            throw new Error(`Invalid ${fieldName} format: ${uuid}`);
        }
    }
}
