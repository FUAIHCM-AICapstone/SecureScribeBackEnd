'use client';

import React, { createContext, useContext, useEffect, useRef, useState, useCallback } from 'react';
import Cookies from 'js-cookie';
import { useAuth } from './AuthContext';

interface WebSocketContextType {
    isConnected: boolean;
    lastMessage: any;
    connect: () => void;
    disconnect: () => void;
    sendMessage: (message: any) => void;
}

interface TaskProgressMessage {
    type: 'task_progress';
    data: {
        task_id: string;
        progress: number;
        status: string;
        estimated_time: string;
        last_update: string;
        task_type: string;
    };
}

interface NotificationMessage {
    type: 'notification';
    data: {
        notification_type: string;
        payload: any;
        channel: string;
        timestamp: number;
    };
}

type WebSocketMessage = TaskProgressMessage | NotificationMessage | { type: string; data: any };

const WebSocketContext = createContext<WebSocketContextType>({
    isConnected: false,
    lastMessage: null,
    connect: () => { },
    disconnect: () => { },
    sendMessage: () => { },
});

export const WebSocketProvider = ({ children }: { children: React.ReactNode }) => {
    const [isConnected, setIsConnected] = useState(false);
    const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
    const wsRef = useRef<WebSocket | null>(null);
    const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
    const reconnectAttempts = useRef(0);
    const maxReconnectAttempts = 1; // Only retry once
    const reconnectInterval = 10000; // 10 seconds delay
    const isConnectingRef = useRef(false); // Prevent multiple simultaneous connections
    const hasConnectedRef = useRef(false); // Track if we've ever successfully connected
    const { logout } = useAuth();

    const getWebSocketUrl = useCallback(() => {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api';
        // Extract host from API base URL (remove /api and /v1 if present)
        const host = apiBaseUrl.replace(/^https?:\/\//, '').replace(/\/api(\/v1)?\/?$/, '');
        const token = Cookies.get('access_token');

        console.log('🔗 WebSocket URL generation:', {
            protocol,
            apiBaseUrl,
            host,
            hasToken: !!token,
            tokenLength: token?.length
        });

        if (!token) {
            console.warn('No access token found for WebSocket connection');
            return null;
        }

        const wsUrl = `${protocol}//${host}/api/v1/notifications/ws?authorization=Bearer%20${token}`;
        console.log('🔗 Generated WebSocket URL:', wsUrl);

        return wsUrl;
    }, []);

    const connect = useCallback(() => {
        // Prevent multiple simultaneous connection attempts and only connect once
        if (isConnectingRef.current || wsRef.current?.readyState === WebSocket.OPEN || hasConnectedRef.current) {
            console.log('WebSocket already connected, connecting, or has connected before');
            return;
        }

        const wsUrl = getWebSocketUrl();
        if (!wsUrl) {
            console.error('Cannot create WebSocket URL: missing access token');
            return;
        }

        try {
            console.log('🔌 Connecting to WebSocket...');
            isConnectingRef.current = true;
            const ws = new WebSocket(wsUrl);
            wsRef.current = ws;

            ws.onopen = () => {
                console.log('✅ WebSocket connected successfully');
                console.log('✅ WebSocket details:', {
                    url: ws.url,
                    protocol: ws.protocol,
                    extensions: ws.extensions,
                    readyState: ws.readyState
                });
                isConnectingRef.current = false;
                setIsConnected(true);
                hasConnectedRef.current = true;
                reconnectAttempts.current = 0;

                // Send initial ping to keep connection alive
                setTimeout(() => {
                    if (ws.readyState === WebSocket.OPEN) {
                        ws.send(JSON.stringify({ type: 'ping' }));
                    }
                }, 1000);
            };

            ws.onmessage = (event) => {
                try {
                    const message: WebSocketMessage = JSON.parse(event.data);
                    console.log('📨 WebSocket message received:', message);
                    console.log('📨 Raw message data:', event.data);

                    setLastMessage(message);

                    // Handle different message types
                    if (message.type === 'task_progress') {
                        console.log('📊 Task progress update:', message.data);
                        console.log('📊 Task ID in message:', message.data?.task_id);
                    } else if (message.type === 'notification') {
                        console.log('🔔 Notification received:', message.data);
                    } else if (message.type === 'pong') {
                        console.log('🏓 Pong received from server');
                    } else if (message.type === 'capabilities') {
                        console.log('⚙️ Server capabilities:', message.data);
                    } else if (message.type === 'connected') {
                        console.log('🔗 WebSocket connection confirmed');
                    } else if (message.type === 'unauthorized' || message.type === 'error') {
                        console.log('🚫 WebSocket unauthorized or error, logging out...');
                        logout();
                        return;
                    }
                } catch (error) {
                    console.error('❌ Failed to parse WebSocket message:', error);
                }
            };

            ws.onclose = (event) => {
                console.log('🔌 WebSocket connection closed:', {
                    code: event.code,
                    reason: event.reason,
                    wasClean: event.wasClean,
                    target: event.target
                });
                isConnectingRef.current = false;
                setIsConnected(false);
                wsRef.current = null;

                // Handle specific error codes
                if (event.code === 4001) {
                    console.log('🚫 WebSocket closed: Unauthorized (4001) - Invalid token, logging out...');
                    logout();
                    return;
                } else if (event.code === 4002) {
                    console.log('🚫 WebSocket closed: User not found (4002), logging out...');
                    logout();
                    return;
                } else if (event.code === 4003) {
                    console.log('🚫 WebSocket closed: Forbidden (4003), logging out...');
                    logout();
                    return;
                } else if (event.code === 1006) {
                    console.log('🚫 WebSocket closed: Abnormal closure (1006) - Connection lost');
                } else if (event.code === 1008) {
                    console.log('🚫 WebSocket closed: Policy violation (1008)');
                } else if (event.code === 1011) {
                    console.log('🚫 WebSocket closed: Server error (1011)');
                } else if (event.reason?.includes('unauthorized') || event.reason?.includes('invalid')) {
                    console.log('🚫 WebSocket closed due to authentication issue, logging out...');
                    logout();
                    return;
                }

                // Only attempt to reconnect if not a normal closure and we haven't exceeded max attempts
                if (event.code !== 1000 && reconnectAttempts.current < maxReconnectAttempts && !hasConnectedRef.current) {
                    console.log(`🔄 Attempting to reconnect... (${reconnectAttempts.current + 1}/${maxReconnectAttempts})`);
                    reconnectAttempts.current++;

                    reconnectTimeoutRef.current = setTimeout(() => {
                        connect();
                    }, reconnectInterval);
                }
            };

            ws.onerror = (error) => {
                console.error('❌ WebSocket error:', error);
                console.error('❌ WebSocket readyState:', ws.readyState);
                console.error('❌ WebSocket URL:', ws.url);
                console.error('❌ WebSocket protocol:', ws.protocol);
                console.error('❌ WebSocket extensions:', ws.extensions);
                isConnectingRef.current = false;
            };

        } catch (error) {
            console.error('❌ Failed to create WebSocket connection:', error);
            isConnectingRef.current = false;
        }
    }, [getWebSocketUrl, logout]);

    const disconnect = useCallback(() => {
        if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current);
            reconnectTimeoutRef.current = null;
        }

        if (wsRef.current) {
            console.log('🔌 Disconnecting WebSocket...');
            wsRef.current.close(1000, 'Client disconnecting');
            wsRef.current = null;
        }

        isConnectingRef.current = false;
        setIsConnected(false);
        reconnectAttempts.current = 0;
        hasConnectedRef.current = false; // Reset connection flag
    }, []);

    const sendMessage = useCallback((message: any) => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            try {
                wsRef.current.send(JSON.stringify(message));
                console.log('📤 Message sent:', message);
            } catch (error) {
                console.error('❌ Failed to send message:', error);
            }
        } else {
            console.warn('⚠️ WebSocket not connected, cannot send message');
        }
    }, []);

    // Single unified connection management
    useEffect(() => {
        const token = Cookies.get('access_token');

        // Only connect if we have a token and haven't connected before
        if (token && !hasConnectedRef.current && !isConnected && wsRef.current?.readyState !== WebSocket.OPEN) {
            console.log('🔌 Initializing WebSocket connection...');
            connect();
        } else if (!token && isConnected) {
            console.log('🚪 No token available, disconnecting...');
            disconnect();
        }

        // Cleanup on unmount
        return () => {
            if (wsRef.current) {
                console.log('🧹 Cleaning up WebSocket connection...');
                disconnect();
            }
        };
    }, [connect, disconnect, isConnected]); // Only depend on these

    const contextValue: WebSocketContextType = {
        isConnected,
        lastMessage,
        connect,
        disconnect,
        sendMessage,
    };

    return (
        <WebSocketContext.Provider value={contextValue}>
            {children}
        </WebSocketContext.Provider>
    );
};

export const useWebSocket = () => {
    const context = useContext(WebSocketContext);
    if (!context) {
        throw new Error('useWebSocket must be used within a WebSocketProvider');
    }
    return context;
};

// Custom hook for task progress monitoring
export const useTaskProgress = (taskId?: string) => {
    const { lastMessage, isConnected } = useWebSocket();
    const [taskProgress, setTaskProgress] = useState<Map<string, any>>(new Map());

    useEffect(() => {
        if (lastMessage?.type === 'task_progress') {
            const progressData = lastMessage.data;
            setTaskProgress(prev => new Map(prev.set(progressData.task_id, progressData)));
        }
    }, [lastMessage]);

    const getTaskProgress = useCallback((id: string) => {
        return taskProgress.get(id) || null;
    }, [taskProgress]);

    const getCurrentTaskProgress = useCallback(() => {
        if (!taskId) return null;

        // First try exact match
        const exactMatch = taskProgress.get(taskId);
        if (exactMatch) return exactMatch;

        // If no exact match, try to find a task that starts with the expected pattern
        // This handles cases where backend adds timestamp suffix (e.g., index_file_123_1234567890)
        for (const [storedTaskId, progressData] of taskProgress.entries()) {
            if (storedTaskId && typeof storedTaskId === 'string' && storedTaskId.startsWith(taskId)) {
                return progressData;
            }
        }

        return null;
    }, [taskId, taskProgress]);

    return {
        taskProgress,
        getTaskProgress,
        getCurrentTaskProgress,
        isConnected,
    };
};
