'use client';

import { useState } from 'react';
import ConversationSidebar from './ConversationSidebar';
import MessageContainer from './MessageContainer';
import ChatInput from './ChatInput';

export default function ChatClientWrapper() {
    const [selectedConversationId, setSelectedConversationId] = useState<string | null>(null);

    const handleSelectConversation = (id: string) => {
        console.log('Selected conversation:', id);
        setSelectedConversationId(id);
    };

    return (
        <>
            <div className="w-80 bg-white border-r border-gray-200">
                <ConversationSidebar
                    onSelectConversation={handleSelectConversation}
                    selectedConversationId={selectedConversationId}
                />
            </div>

            <div className="flex-1 flex flex-col">
                {selectedConversationId ? (
                    <>
                        <MessageContainer conversationId={selectedConversationId} />
                        <ChatInput conversationId={selectedConversationId} />
                    </>
                ) : (
                    <div className="flex-1 flex items-center justify-center text-gray-500">
                        Select a conversation to start chatting
                    </div>
                )}
            </div>
        </>
    );
}
