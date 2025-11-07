'use client';

import React, { useState, useEffect } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
    createMeetingNote,
    getMeetingNote,
    updateMeetingNote,
    deleteMeetingNote,
} from '../../services/api/meetingNote';
import { PREDEFINED_SECTIONS } from '../../types/meeting.type';
import type { MeetingNoteResponse } from '../../types/meeting_note.type';

interface MeetingNoteManagerProps {
    meetingId: string;
    initialNote?: MeetingNoteResponse | null;
}

const MeetingNoteManager: React.FC<MeetingNoteManagerProps> = ({
    meetingId,
    initialNote,
}) => {
    const queryClient = useQueryClient();
    const [isOpen, setIsOpen] = useState(false);
    const [content, setContent] = useState('');
    const [selectedSections, setSelectedSections] = useState<string[]>([]);
    const [summaryPreview, setSummaryPreview] = useState('');

    // Use initialNote if provided, otherwise fetch via API
    const { data: note = initialNote } = useQuery({
        queryKey: ['meeting-note', meetingId],
        queryFn: () => getMeetingNote(meetingId),
        enabled: !!meetingId && !initialNote,
        initialData: initialNote || undefined,
    });

    // Populate form when note changes
    useEffect(() => {
        if (note?.content) {
            setContent(note.content);
            setSummaryPreview(note.content);
        }
    }, [note]);

    const createMutation = useMutation({
        mutationFn: () => createMeetingNote({ meeting_id: meetingId }),
        onSuccess: (data) => {
            setContent(data.content);
            setSummaryPreview(data.content);
            queryClient.invalidateQueries({
                queryKey: ['meeting-note', meetingId],
            });
            setIsOpen(true);
        },
    });

    const updateMutation = useMutation({
        mutationFn: (content: string) =>
            updateMeetingNote(meetingId, { content }),
        onSuccess: () => {
            queryClient.invalidateQueries({
                queryKey: ['meeting-note', meetingId],
            });
            setIsOpen(false);
        },
    });

    const deleteMutation = useMutation({
        mutationFn: () => deleteMeetingNote(meetingId),
        onSuccess: () => {
            queryClient.invalidateQueries({
                queryKey: ['meeting-note', meetingId],
            });
            setIsOpen(false);
            setContent('');
            setSelectedSections([]);
        },
    });

    const handleOpenModal = () => {
        if (note?.content) {
            setContent(note.content);
        }
        setIsOpen(true);
    };

    const handleCreateNote = () => {
        createMutation.mutate();
    };

    const handleSaveNote = () => {
        updateMutation.mutate(content || '');
    };

    const handleDeleteNote = () => {
        if (confirm('Are you sure you want to delete this note?')) {
            deleteMutation.mutate();
        }
    };

    const toggleSection = (section: string) => {
        setSelectedSections((prev) =>
            prev.includes(section)
                ? prev.filter((s) => s !== section)
                : [...prev, section]
        );
    };

    return (
        <div className="mb-8">
            <div className="flex justify-between items-center mb-4">
                <h2 className="text-2xl font-semibold">Meeting Notes</h2>
                {note ? (
                    <button
                        onClick={handleOpenModal}
                        className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md text-sm font-medium"
                    >
                        Edit Note
                    </button>
                ) : (
                    <button
                        onClick={handleCreateNote}
                        disabled={createMutation.isPending}
                        className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-md text-sm font-medium disabled:bg-gray-400"
                    >
                        {createMutation.isPending ? 'Creating...' : 'Create Note'}
                    </button>
                )}
            </div>

            {note && (
                <div className="bg-gray-100 dark:bg-gray-800 p-4 rounded-md mb-4">
                    <p className="text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
                        {note.content}
                    </p>
                    <p className="text-sm text-gray-500 mt-2">
                        Last edited:{' '}
                        {note.last_edited_at
                            ? new Date(note.last_edited_at).toLocaleString()
                            : 'N/A'}
                    </p>
                </div>
            )}

            {isOpen && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                    <div className="bg-white dark:bg-gray-900 rounded-lg p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
                        <h3 className="text-xl font-bold mb-4">
                            {note ? 'Edit Note' : 'Create Note'}
                        </h3>

                        {summaryPreview && !note && (
                            <div className="mb-4 p-3 bg-blue-50 dark:bg-blue-900 rounded">
                                <p className="text-sm font-semibold mb-2">
                                    Auto-generated Summary:
                                </p>
                                <p className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
                                    {summaryPreview}
                                </p>
                            </div>
                        )}

                        <textarea
                            value={content}
                            onChange={(e) => setContent(e.target.value)}
                            placeholder="Enter note content..."
                            className="w-full h-40 p-3 border rounded-md dark:bg-gray-800 dark:text-white mb-4"
                        />

                        <div className="mb-4">
                            <label htmlFor="sections" className="block text-sm font-medium mb-2">
                                Sections:
                            </label>
                            <div id="sections" className="flex flex-wrap gap-2">
                                {PREDEFINED_SECTIONS.map((section) => (
                                    <button
                                        key={section}
                                        onClick={() => toggleSection(section)}
                                        className={`px-3 py-1 rounded text-sm font-medium transition ${selectedSections.includes(section)
                                            ? 'bg-blue-600 text-white'
                                            : 'bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-gray-100'
                                            }`}
                                    >
                                        {section}
                                    </button>
                                ))}
                            </div>
                        </div>

                        <div className="flex justify-end gap-2">
                            <button
                                onClick={() => setIsOpen(false)}
                                className="px-4 py-2 bg-gray-300 dark:bg-gray-700 text-gray-900 dark:text-white rounded-md text-sm font-medium"
                            >
                                Cancel
                            </button>
                            {note && (
                                <button
                                    onClick={handleDeleteNote}
                                    disabled={deleteMutation.isPending}
                                    className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-md text-sm font-medium disabled:bg-gray-400"
                                >
                                    {deleteMutation.isPending ? 'Deleting...' : 'Delete'}
                                </button>
                            )}
                            <button
                                onClick={handleSaveNote}
                                disabled={
                                    updateMutation.isPending ||
                                    createMutation.isPending
                                }
                                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md text-sm font-medium disabled:bg-gray-400"
                            >
                                {updateMutation.isPending ? 'Saving...' : 'Save'}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default MeetingNoteManager;
