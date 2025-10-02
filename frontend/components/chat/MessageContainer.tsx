'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { getConversation, connectToChatSSE, disconnectFromChatSSE } from '@/services/api/chat';
import { formatMessageWithMentions } from '@/services/api/chat';
import type { ChatMessageResponse } from '../../types/chat.type';

interface MessageContainerProps {
    conversationId: string;
}

export default function MessageContainer({ conversationId }: MessageContainerProps) {
    const [messages, setMessages] = useState<ChatMessageResponse[]>([]);
    const [loading, setLoading] = useState(true);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    const loadMessages = useCallback(async () => {
        try {
            setLoading(true);
            console.log('Loading messages for conversation:', conversationId);
            const conversation = await getConversation(conversationId, 50);
            console.log('Messages loaded:', conversation.messages);
            setMessages(conversation.messages);
        } catch (error) {
            console.error('Failed to load messages:', error);
        } finally {
            setLoading(false);
        }
    }, [conversationId]);

    useEffect(() => {
        loadMessages();
        console.log('Connecting to SSE for conversation:', conversationId);
        const eventSource = connectToChatSSE(
            conversationId,
            (data) => {
                console.log('SSE message received:', data);
                if (data.type === 'chat_message' && data.message) {
                    setMessages(prev => [...(prev || []), data.message]);
                }
            },
            (error) => console.error('SSE error:', error)
        );

        return () => {
            console.log('Disconnecting SSE for conversation:', conversationId);
            disconnectFromChatSSE(eventSource);
        };
    }, [conversationId, loadMessages]);

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    return (
        <div className="flex-1 overflow-y-auto p-4">
            {loading ? (
                <div className="flex justify-center py-8">
                    <div className="text-gray-500">Loading messages...</div>
                </div>
            ) : !messages || messages.length === 0 ? (
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
