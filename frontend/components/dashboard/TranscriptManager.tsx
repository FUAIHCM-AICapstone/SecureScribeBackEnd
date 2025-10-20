'use client';

import React, { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
    getTranscriptsByMeeting,
    updateTranscript,
    deleteTranscript,
} from '../../services/api/transcript';
import type { TranscriptResponse, TranscriptUpdate } from '../../types/transcript.type';

interface TranscriptManagerProps {
    meetingId: string;
    initialTranscripts?: TranscriptResponse[];
}

const TranscriptManager: React.FC<TranscriptManagerProps> = ({ meetingId, initialTranscripts }) => {
    const queryClient = useQueryClient();
    const [searchQuery, setSearchQuery] = useState('');
    const [isViewerOpen, setIsViewerOpen] = useState(false);
    const [selectedTranscript, setSelectedTranscript] =
        useState<TranscriptResponse | null>(null);
    const [isEditMode, setIsEditMode] = useState(false);
    const [editContent, setEditContent] = useState('');
    const fileInputRef = React.useRef<HTMLInputElement>(null);

    // Use initialTranscripts if provided, otherwise fetch via API
    const { data: transcripts = initialTranscripts || [], isLoading } = useQuery({
        queryKey: ['transcripts', meetingId],
        queryFn: () => getTranscriptsByMeeting(meetingId),
        enabled: !!meetingId && (!initialTranscripts || initialTranscripts.length === 0),
        initialData: initialTranscripts || [],
    });

    const updateTranscriptMutation = useMutation({
        mutationFn: (payload: TranscriptUpdate) =>
            updateTranscript(selectedTranscript!.id, payload),
        onSuccess: (data) => {
            setSelectedTranscript(data);
            setIsEditMode(false);
            queryClient.invalidateQueries({
                queryKey: ['transcripts', meetingId],
            });
        },
    });

    const deleteTranscriptMutation = useMutation({
        mutationFn: () => deleteTranscript(selectedTranscript!.id),
        onSuccess: () => {
            queryClient.invalidateQueries({
                queryKey: ['transcripts', meetingId],
            });
            setIsViewerOpen(false);
            setSelectedTranscript(null);
        },
    });

    const filteredTranscripts = transcripts.filter((t) =>
        t.content?.toLowerCase().includes(searchQuery.toLowerCase())
    );

    const handleViewTranscript = (transcript: TranscriptResponse) => {
        setSelectedTranscript(transcript);
        setEditContent(transcript.content || '');
        setIsViewerOpen(true);
    };

    const handleCopyText = () => {
        if (selectedTranscript?.content) {
            navigator.clipboard.writeText(selectedTranscript.content);
        }
    };

    const handleSaveEdit = () => {
        updateTranscriptMutation.mutate({ content: editContent });
    };

    const handleDeleteTranscript = () => {
        if (confirm('Are you sure you want to delete this transcript?')) {
            deleteTranscriptMutation.mutate();
        }
    };

    const handleAudioUpload = async (
        event: React.ChangeEvent<HTMLInputElement>
    ) => {
        const file = event.target.files?.[0];
        if (file) {
            console.log('File selected:', file.name);
        }
    };

    return (
        <div className="mb-8">
            <div className="flex justify-between items-center mb-4">
                <h2 className="text-2xl font-semibold">Transcripts</h2>
                <button
                    onClick={() => fileInputRef.current?.click()}
                    className="px-4 py-2 bg-orange-600 hover:bg-orange-700 text-white rounded-md text-sm font-medium"
                >
                    ⬆ Upload & Transcribe
                </button>
                <input
                    ref={fileInputRef}
                    type="file"
                    accept="audio/*"
                    onChange={handleAudioUpload}
                    className="hidden"
                />
            </div>

            <div className="mb-4">
                <input
                    type="text"
                    placeholder="Search transcripts..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full px-3 py-2 border rounded-md dark:bg-gray-800 dark:text-white"
                />
            </div>

            {isLoading ? (
                <div className="text-center py-8">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
                </div>
            ) : filteredTranscripts.length === 0 ? (
                <div className="text-center py-8 text-gray-500">
                    No transcripts found
                </div>
            ) : (
                <div className="space-y-2">
                    {filteredTranscripts.map((transcript) => (
                        <button
                            key={transcript.id}
                            onClick={() => handleViewTranscript(transcript)}
                            className="w-full text-left p-3 bg-gray-100 dark:bg-gray-800 rounded-md hover:bg-gray-200 dark:hover:bg-gray-700 transition"
                        >
                            <div className="flex justify-between items-center">
                                <div>
                                    <p className="font-medium truncate">
                                        {transcript.content?.substring(0, 60)}
                                        {(transcript.content?.length || 0) > 60
                                            ? '...'
                                            : ''}
                                    </p>
                                    <p className="text-sm text-gray-500">
                                        {new Date(
                                            transcript.created_at
                                        ).toLocaleString()}
                                    </p>
                                </div>
                                <span className="text-xs bg-orange-200 text-orange-800 px-2 py-1 rounded">
                                    View
                                </span>
                            </div>
                        </button>
                    ))}
                </div>
            )}

            {isViewerOpen && selectedTranscript && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                    <div className="bg-white dark:bg-gray-900 rounded-lg p-6 w-full max-w-3xl max-h-[90vh] overflow-y-auto">
                        <div className="flex justify-between items-center mb-4">
                            <h3 className="text-xl font-bold">
                                {isEditMode
                                    ? 'Edit Transcript'
                                    : 'View Transcript'}
                            </h3>
                            <button
                                onClick={() => setIsViewerOpen(false)}
                                className="text-gray-500 hover:text-gray-700 text-2xl"
                            >
                                ×
                            </button>
                        </div>

                        <p className="text-sm text-gray-500 mb-4">
                            Created:{' '}
                            {new Date(
                                selectedTranscript.created_at
                            ).toLocaleString()}
                        </p>

                        {isEditMode ? (
                            <textarea
                                value={editContent}
                                onChange={(e) =>
                                    setEditContent(e.target.value)
                                }
                                className="w-full h-64 p-3 border rounded-md dark:bg-gray-800 dark:text-white mb-4"
                            />
                        ) : (
                            <div className="bg-gray-50 dark:bg-gray-800 p-4 rounded-md mb-4 max-h-64 overflow-y-auto">
                                <p className="text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
                                    {selectedTranscript.content}
                                </p>
                            </div>
                        )}

                        <div className="flex justify-end gap-2">
                            <button
                                onClick={() => setIsViewerOpen(false)}
                                className="px-4 py-2 bg-gray-300 dark:bg-gray-700 text-gray-900 dark:text-white rounded-md text-sm font-medium"
                            >
                                Close
                            </button>
                            {!isEditMode && (
                                <button
                                    onClick={handleCopyText}
                                    className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md text-sm font-medium"
                                >
                                    📋 Copy
                                </button>
                            )}
                            {!isEditMode && (
                                <button
                                    onClick={() => setIsEditMode(true)}
                                    className="px-4 py-2 bg-yellow-600 hover:bg-yellow-700 text-white rounded-md text-sm font-medium"
                                >
                                    ✏️ Edit
                                </button>
                            )}
                            {isEditMode && (
                                <button
                                    onClick={() => setIsEditMode(false)}
                                    className="px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded-md text-sm font-medium"
                                >
                                    Cancel
                                </button>
                            )}
                            {isEditMode && (
                                <button
                                    onClick={handleSaveEdit}
                                    disabled={
                                        updateTranscriptMutation.isPending
                                    }
                                    className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-md text-sm font-medium disabled:bg-gray-400"
                                >
                                    {updateTranscriptMutation.isPending
                                        ? 'Saving...'
                                        : 'Save'}
                                </button>
                            )}
                            <button
                                onClick={handleDeleteTranscript}
                                disabled={
                                    deleteTranscriptMutation.isPending
                                }
                                className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-md text-sm font-medium disabled:bg-gray-400"
                            >
                                {deleteTranscriptMutation.isPending
                                    ? 'Deleting...'
                                    : 'Delete'}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default TranscriptManager;
