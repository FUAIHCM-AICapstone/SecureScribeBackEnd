'use client';

import { useEffect, useRef, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { connectToChatSSE, disconnectFromChatSSE } from '@/services/api/chat';
import { getConversationWithMessages } from '@/services/api/conversation';
import { queryKeys } from '@/lib/queryClient';
import { formatMessageWithMentions } from '@/services/api/chat';

interface MessageContainerProps {
    conversationId: string;
}

export default function MessageContainer({ conversationId }: MessageContainerProps) {
    const messagesEndRef = useRef<HTMLDivElement>(null);

    // Fetch messages using React Query
    const { data: conversation, isLoading, error } = useQuery({
        queryKey: queryKeys.conversationMessages(conversationId),
        queryFn: () => getConversationWithMessages(conversationId, 50),
        enabled: !!conversationId,
        staleTime: 10000, // 10 seconds
    });

    const messages = useMemo(() => conversation?.messages || [], [conversation?.messages]);

    // Set up SSE connection for real-time updates
    useEffect(() => {
        if (!conversationId) return;

        console.log('Connecting to SSE for conversation:', conversationId);
        const eventSource = connectToChatSSE(
            conversationId,
            (data) => {
                console.log('SSE message received:', data);
                // Note: In a real app, you'd want to refetch the conversation data
                // or update the query cache when new messages arrive
            },
            (error) => console.error('SSE error:', error)
        );

        return () => {
            console.log('Disconnecting SSE for conversation:', conversationId);
            disconnectFromChatSSE(eventSource);
        };
    }, [conversationId]);

    useEffect(() => {
        scrollToBottom();
    }, [messages]); // messages is now memoized, so this won't cause infinite re-renders

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    return (
        <div className="flex-1 overflow-y-auto p-4">
            {isLoading ? (
                <div className="flex justify-center py-8">
                    <div className="text-gray-500">Loading messages...</div>
                </div>
            ) : error ? (
                <div className="flex justify-center py-8">
                    <div className="text-red-500">Failed to load messages</div>
                </div>
            ) : messages.length === 0 ? (
                <div className="flex justify-center py-8">
                    <div className="text-gray-500">No messages yet. Start the conversation!</div>
                </div>
            ) : (
                <div className="space-y-4">
                    {messages.map((message) => (
                        <div
                            key={message.id}
                            className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                        >
                            <div
                                className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${message.role === 'user'
                                    ? 'bg-blue-500 text-white'
                                    : 'bg-gray-200 text-gray-800'
                                    }`}
                            >
                                <div
                                    className="text-sm"
                                    dangerouslySetInnerHTML={{
                                        __html: formatMessageWithMentions(message.content, message.mentions || [])
                                    }}
                                />
                                <div className="text-xs mt-1 opacity-70">
                                    {new Date(message.timestamp).toLocaleTimeString()}
                                </div>
                            </div>
                        </div>
                    ))}
                    <div ref={messagesEndRef} />
                </div>
            )}
        </div>
    );
}
