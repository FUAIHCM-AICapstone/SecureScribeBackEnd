'use client';

import { useRouter, useSearchParams } from 'next/navigation';
import React, { useEffect, useState } from 'react';
import { showToast } from '../../../hooks/useShowToast';
import { handleGoogleCalendarCallback } from '../../../services/api/googleCalendar';

const GoogleCalendarCallbackPage: React.FC = () => {
    const [isProcessing, setIsProcessing] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const searchParams = useSearchParams();
    const router = useRouter();

    useEffect(() => {
        const handleCallback = async () => {
            try {
                const code = searchParams.get('code');
                const errorParam = searchParams.get('error');

                if (errorParam) {
                    console.error('OAuth error:', errorParam);
                    showToast('error', 'Lỗi xác thực Google Calendar. Vui lòng thử lại.');
                    setError('OAuth authentication failed');
                    setIsProcessing(false);
                    return;
                }

                if (!code) {
                    console.error('No authorization code received');
                    showToast('error', 'Không nhận được mã xác thực. Vui lòng thử lại.');
                    setError('No authorization code received');
                    setIsProcessing(false);
                    return;
                }

                // Process the callback
                await handleGoogleCalendarCallback(code);

                showToast('success', 'Google Calendar đã được kết nối thành công!');

                // Redirect back to dashboard after a short delay
                setTimeout(() => {
                    router.push('/dashboard');
                }, 2000);

            } catch (error) {
                console.error('Failed to handle Google Calendar callback:', error);
                showToast('error', 'Không thể kết nối Google Calendar. Vui lòng thử lại.');
                setError('Failed to connect Google Calendar');
                setIsProcessing(false);
            }
        };

        handleCallback();
    }, [searchParams, router]);

    if (isProcessing) {
        return (
            <div className="flex items-center justify-center min-h-screen bg-gray-50 dark:bg-gray-900">
                <div className="text-center">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
                    <p className="text-lg font-medium text-gray-900 dark:text-white">
                        Đang kết nối Google Calendar...
                    </p>
                    <p className="text-sm text-gray-600 dark:text-gray-400 mt-2">
                        Vui lòng đợi trong giây lát
                    </p>
                </div>
            </div>
        );
    }

    return (
        <div className="flex items-center justify-center min-h-screen bg-gray-50 dark:bg-gray-900">
            <div className="text-center">
                <div className="text-6xl mb-4">
                    {error ? '❌' : '✅'}
                </div>
                <p className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                    {error ? 'Kết nối thất bại' : 'Kết nối thành công'}
                </p>
                <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
                    {error
                        ? 'Đã xảy ra lỗi khi kết nối Google Calendar'
                        : 'Google Calendar đã được kết nối thành công'
                    }
                </p>
                <button
                    onClick={() => router.push('/dashboard')}
                    className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md text-sm font-medium"
                >
                    Quay lại Dashboard
                </button>
            </div>
        </div>
    );
};

export default GoogleCalendarCallbackPage;
