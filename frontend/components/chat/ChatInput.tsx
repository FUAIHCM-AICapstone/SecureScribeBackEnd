'use client';

import { useState, FormEvent } from 'react';
import { sendChatMessage, parseMentions } from '@/services/api/chat';

interface ChatInputProps {
    conversationId: string;
}

export default function ChatInput({ conversationId }: ChatInputProps) {
    const [message, setMessage] = useState('');
    const [sending, setSending] = useState(false);

    const handleSubmit = async (e: FormEvent) => {
        e.preventDefault();
        if (!message.trim() || sending) return;

        try {
            setSending(true);
            console.log('Sending message for conversation:', conversationId);

            // Parse mentions from message content
            const mentions = parseMentions(message);
            console.log('Parsed mentions:', mentions);

            const response = await sendChatMessage(conversationId, {
                content: message.trim(),
                mentions,
            });

            console.log('Message sent successfully:', response);
            setMessage('');
        } catch (error) {
            console.error('Failed to send message:', error);
        } finally {
            setSending(false);
        }
    };

    return (
        <div className="border-t border-gray-200 p-4">
            <form onSubmit={handleSubmit} className="flex space-x-3">
                <div className="flex-1">
                    <textarea
                        value={message}
                        onChange={(e) => setMessage(e.target.value)}
                        placeholder="Type a message... (use @project:uuid @meeting:uuid for mentions)"
                        className="w-full p-3 border border-gray-300 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        rows={3}
                        disabled={sending}
                    />
                </div>
                <div className="flex-shrink-0">
                    <button
                        type="submit"
                        disabled={!message.trim() || sending}
                        className="h-full px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        {sending ? 'Sending...' : 'Send'}
                    </button>
                </div>
            </form>

            {message && (
                <div className="mt-2 text-xs text-gray-500">
                    Detected mentions: {parseMentions(message).length > 0 ? parseMentions(message).map(m => `@${m.entity_type}:${m.entity_id.substring(0, 8)}...`).join(', ') : 'None'}
                </div>
            )}
        </div>
    );
}
