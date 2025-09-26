'use client';

import { useQuery } from '@tanstack/react-query';
import React, { useEffect, useState } from 'react';
import { showToast } from '../../hooks/useShowToast';
import { queryKeys } from '../../lib/queryClient';
import {
    connectGoogleCalendar,
    getGoogleCalendarEvents,
    getGoogleCalendarIntegrationStatus
} from '../../services/api/googleCalendar';
import { GoogleCalendarEvent } from '../../types/googleCalendar.type';

const GoogleCalendarSection: React.FC = () => {
    const [isConnecting, setIsConnecting] = useState(false);
    const [isConnected, setIsConnected] = useState(false);

    // Query for Google Calendar events
    const { data: eventsData, isLoading: eventsLoading, error: eventsError } = useQuery({
        queryKey: queryKeys.googleCalendar,
        queryFn: getGoogleCalendarEvents,
        enabled: isConnected,
        refetchInterval: 5 * 60 * 1000, // Refetch every 5 minutes
    });

    // Query for integration status
    const { data: statusData } = useQuery({
        queryKey: ['google-calendar-status'],
        queryFn: getGoogleCalendarIntegrationStatus,
        refetchInterval: 30 * 1000, // Refetch every 30 seconds
    });

    const events = eventsData || [];
    const loading = eventsLoading;
    const error = eventsError?.message || null;

    useEffect(() => {
        if (statusData) {
            setIsConnected(statusData.connected);
        }
    }, [statusData]);

    const handleConnect = async () => {
        try {
            setIsConnecting(true);
            const response = await connectGoogleCalendar();

            // Redirect to Google OAuth
            window.location.href = response.auth_url;
        } catch (error) {
            console.error('Failed to connect Google Calendar:', error);
            showToast('error', 'Không thể kết nối với Google Calendar. Vui lòng thử lại.');
            setIsConnecting(false);
        }
    };

    const handleDisconnect = async () => {
        try {
            // For now, we'll just set the state to disconnected
            // In a real implementation, you might want to call a disconnect endpoint
            setIsConnected(false);
            showToast('success', 'Đã ngắt kết nối Google Calendar');
        } catch (error) {
            console.error('Failed to disconnect Google Calendar:', error);
            showToast('error', 'Không thể ngắt kết nối Google Calendar. Vui lòng thử lại.');
        }
    };

    const formatEventDate = (event: GoogleCalendarEvent) => {
        if (!event.start) return 'No date';

        if (event.start.dateTime) {
            return new Date(event.start.dateTime).toLocaleString('vi-VN');
        } else if (event.start.date) {
            return new Date(event.start.date).toLocaleDateString('vi-VN');
        }
        return 'No date';
    };

    const formatEventTime = (event: GoogleCalendarEvent) => {
        if (!event.start || !event.end) return '';

        const startDate = event.start.dateTime ? new Date(event.start.dateTime) : new Date(event.start.date as string);
        const endDate = event.end.dateTime ? new Date(event.end.dateTime) : new Date(event.end.date as string);

        if (event.start.dateTime && event.end.dateTime) {
            return `${startDate.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })} - ${endDate.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })}`;
        } else if (event.start.date && event.end.date) {
            if (event.start.date === event.end.date) {
                return 'Cả ngày';
            }
            return `${startDate.toLocaleDateString('vi-VN')} - ${endDate.toLocaleDateString('vi-VN')}`;
        }
        return '';
    };

    if (loading) {
        return (
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
                <div className="flex items-center justify-center py-8">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                    <span className="ml-2 text-gray-600 dark:text-gray-400">Đang tải sự kiện...</span>
                </div>
            </div>
        );
    }

    return (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
            <div className="flex justify-between items-start mb-4">
                <div>
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                        Google Calendar
                    </h3>
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                        {isConnected ? 'Đã kết nối' : 'Chưa kết nối'}
                    </p>
                </div>
                <div className="flex gap-2">
                    {!isConnected ? (
                        <button
                            onClick={handleConnect}
                            disabled={isConnecting}
                            className="flex items-center px-3 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white rounded-md text-sm font-medium transition-colors"
                        >
                            {isConnecting ? (
                                <>
                                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                                    Đang kết nối...
                                </>
                            ) : (
                                <>
                                    <span className="mr-2">🔗</span>
                                    Kết nối
                                </>
                            )}
                        </button>
                    ) : (
                        <button
                            onClick={handleDisconnect}
                            className="flex items-center px-3 py-2 bg-red-600 hover:bg-red-700 text-white rounded-md text-sm font-medium transition-colors"
                        >
                            <span className="mr-2">🔌</span>
                            Ngắt kết nối
                        </button>
                    )}
                </div>
            </div>

            {error && (
                <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md">
                    <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
                </div>
            )}

            {isConnected && events.length > 0 && (
                <div className="space-y-3">
                    <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300">
                        Sự kiện sắp tới ({events.length})
                    </h4>
                    <div className="space-y-2 max-h-64 overflow-y-auto">
                        {events.slice(0, 5).map((event, index) => (
                            <div
                                key={event.id || index}
                                className="p-3 bg-gray-50 dark:bg-gray-700 rounded-md border border-gray-200 dark:border-gray-600"
                            >
                                <div className="flex justify-between items-start">
                                    <div className="flex-1">
                                        <h5 className="font-medium text-gray-900 dark:text-white text-sm">
                                            {event.summary || 'Sự kiện không có tiêu đề'}
                                        </h5>
                                        {event.description && (
                                            <p className="text-xs text-gray-600 dark:text-gray-400 mt-1 line-clamp-2">
                                                {event.description}
                                            </p>
                                        )}
                                    </div>
                                </div>
                                <div className="mt-2 flex justify-between items-center text-xs text-gray-500 dark:text-gray-400">
                                    <span>{formatEventDate(event)}</span>
                                    <span>{formatEventTime(event)}</span>
                                </div>
                            </div>
                        ))}
                    </div>
                    {events.length > 5 && (
                        <p className="text-xs text-gray-500 dark:text-gray-400 text-center">
                            ... và {events.length - 5} sự kiện khác
                        </p>
                    )}
                </div>
            )}

            {isConnected && events.length === 0 && (
                <div className="text-center py-8">
                    <div className="text-gray-400 dark:text-gray-500 mb-2">
                        <span className="text-2xl">📅</span>
                    </div>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                        Không có sự kiện nào trong thời gian tới
                    </p>
                </div>
            )}

            {!isConnected && (
                <div className="text-center py-8">
                    <div className="text-gray-400 dark:text-gray-500 mb-2">
                        <span className="text-2xl">🔗</span>
                    </div>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                        Kết nối với Google Calendar để xem sự kiện của bạn
                    </p>
                </div>
            )}
        </div>
    );
};

export default GoogleCalendarSection;
