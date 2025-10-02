'use client';

import { useState, useEffect } from 'react';
import { getConversations, createConversation } from '@/services/api/conversation';
import type { ConversationResponse } from '../../types/conversation.type';

interface ConversationSidebarProps {
    onSelectConversation: (id: string) => void;
    selectedConversationId: string | null;
}

export default function ConversationSidebar({
    onSelectConversation,
    selectedConversationId,
}: ConversationSidebarProps) {
    const [conversations, setConversations] = useState<ConversationResponse[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        loadConversations();
    }, []);

    const loadConversations = async () => {
        try {
            setLoading(true);
            const response = await getConversations(1, 20);
            console.log('Conversations loaded:', response);
            setConversations(response as ConversationResponse[]);
        } catch (error) {
            console.error('Failed to load conversations:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleCreateConversation = async () => {
        try {
            const newConversation = await createConversation({ title: 'New Chat' });
            setConversations(prev => [newConversation, ...(prev || [])]);
            onSelectConversation(newConversation.id);
        } catch (error) {
            console.error('Failed to create conversation:', error);
        }
    };

    return (
        <div className="h-full flex flex-col">
            <div className="p-4 border-b border-gray-200">
                <div className="flex items-center justify-between">
                    <h2 className="text-lg font-semibold">Conversations</h2>
                    <button
                        onClick={handleCreateConversation}
                        className="px-3 py-1 bg-blue-500 text-white rounded text-sm hover:bg-blue-600"
                    >
                        New Chat
                    </button>
                </div>
            </div>

            <div className="flex-1 overflow-y-auto">
                {loading ? (
                    <div className="p-4 text-center text-gray-500">Loading...</div>
                ) : !conversations || conversations.length === 0 ? (
                    <div className="p-4 text-center text-gray-500">No conversations yet</div>
                ) : (
                    conversations.map((conversation) => (
                        <div
                            key={conversation.id}
                            onClick={() => {
                                console.log('Clicked conversation:', conversation.id);
                                onSelectConversation(conversation.id);
                            }}
                            onKeyDown={(e) => {
                                if (e.key === 'Enter' || e.key === ' ') {
                                    e.preventDefault();
                                    console.log('Keyboard selected conversation:', conversation.id);
                                    onSelectConversation(conversation.id);
                                }
                            }}
                            tabIndex={0}
                            role="button"
                            className={`p-3 border-b border-gray-100 cursor-pointer hover:bg-gray-50 ${selectedConversationId === conversation.id ? 'bg-blue-50 border-blue-200' : ''
                                }`}
                        >
                            <div className="font-medium text-sm truncate">
                                {conversation.title || 'Untitled Chat'}
                            </div>
                            <div className="text-xs text-gray-500 mt-1">
                                {conversation.message_count || 0} messages
                            </div>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
}
