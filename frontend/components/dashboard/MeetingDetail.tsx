'use client';

import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getMeeting } from '../../services/api/meeting';
import { getMeetingFiles } from '../../services/api/file';
import { queryKeys } from '../../lib/queryClient';
import { showToast } from '../../hooks/useShowToast';
// Types are inferred from React Query data
import FileCard from './FileCard';
import FileUploadModal from './FileUploadModal';
import MeetingNoteManager from './MeetingNoteManager';
import TranscriptManager from './TranscriptManager';

// MeetingDetail component for displaying meeting files

interface MeetingDetailProps {
    meetingId: string;
    onBack: () => void;
}

const MeetingDetail: React.FC<MeetingDetailProps> = ({ meetingId, onBack }) => {
    // Modal states
    const [showFileUpload, setShowFileUpload] = useState(false);

    // React Query hooks for data fetching
    const { data: meetingData, isLoading: meetingLoading, error: meetingError } = useQuery({
        queryKey: queryKeys.meeting(meetingId),
        queryFn: () => getMeeting(meetingId),
    });

    const { data: filesData, isLoading: filesLoading, error: filesError } = useQuery({
        queryKey: queryKeys.meetingFiles(meetingId),
        queryFn: () => getMeetingFiles(meetingId, { limit: 20 }),
    });

    // Show error messages for failed queries
    if (meetingError) {
        console.error('Failed to load meeting:', meetingError);
        showToast('error', 'Không thể tải thông tin cuộc họp. Vui lòng thử lại.');
    }
    if (filesError) {
        console.error('Failed to load files:', filesError);
        showToast('error', 'Không thể tải danh sách tệp tin. Vui lòng thử lại.');
    }

    // Extract data from queries
    const meeting = meetingData || null;
    const files = filesData?.data || [];
    const meetingNote = meetingData?.meeting_note || null;
    const transcripts = meetingData?.transcripts || [];

    // Combined loading state
    const loading = meetingLoading || filesLoading;

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'active': return 'bg-green-200 text-green-600';
            case 'completed': return 'bg-blue-200 text-blue-600';
            case 'cancelled': return 'bg-red-200 text-red-600';
            default: return 'bg-gray-200 text-gray-600';
        }
    };

    const getStatusText = (status: string) => {
        switch (status) {
            case 'active': return 'Hoạt động';
            case 'completed': return 'Hoàn thành';
            case 'cancelled': return 'Đã hủy';
            default: return 'Không xác định';
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-screen">
                <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600"></div>
            </div>
        );
    }

    if (!meeting) {
        return (
            <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                    <div className="text-center">
                        <h1 className="text-2xl font-bold mb-4">Không tìm thấy cuộc họp</h1>
                        <button
                            onClick={onBack}
                            className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded"
                        >
                            Quay lại
                        </button>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                {/* Header */}
                <div className="mb-8">
                    <button
                        onClick={onBack}
                        className="mb-4 text-blue-600 hover:text-blue-700 flex items-center"
                    >
                        ← Quay lại Dashboard
                    </button>
                    <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
                        {meeting.title || 'Chưa có tiêu đề'}
                    </h1>
                    <p className="text-gray-600 dark:text-gray-400">
                        {meeting.description || 'Không có mô tả'}
                    </p>
                    <div className="flex items-center space-x-4 mt-4 text-sm text-gray-500">
                        <span className={`px-2 py-1 text-xs rounded ${getStatusColor(meeting.status)}`}>
                            {getStatusText(meeting.status)}
                        </span>
                        {meeting.is_personal && (
                            <span className="px-2 py-1 text-xs bg-purple-200 text-purple-600 rounded">
                                Cá nhân
                            </span>
                        )}
                        {meeting.start_time && (
                            <span>🕐 {new Date(meeting.start_time).toLocaleString('vi-VN')}</span>
                        )}
                        <span>{meeting.projects?.length || 0} dự án liên quan</span>
                        <span>Tạo ngày: {new Date(meeting.created_at).toLocaleDateString('vi-VN')}</span>
                    </div>
                    {meeting.url && (
                        <div className="mt-4">
                            <a
                                href={meeting.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-blue-600 hover:text-blue-700 underline"
                            >
                                🔗 Link họp
                            </a>
                        </div>
                    )}
                </div>

                {/* Meeting Notes Section */}
                <MeetingNoteManager meetingId={meetingId} initialNote={meetingNote} />

                {/* Transcripts Section */}
                <TranscriptManager meetingId={meetingId} initialTranscripts={transcripts} />

                {/* Files Section */}
                <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6">
                    <div className="flex justify-between items-center mb-6">
                        <h2 className="text-2xl font-semibold">Tệp tin trong cuộc họp ({files.length})</h2>
                        <button
                            onClick={() => setShowFileUpload(true)}
                            className="flex items-center px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-md text-sm font-medium"
                        >
                            <span className="mr-2">⬆</span>
                            Tải lên tệp tin
                        </button>
                    </div>
                    {files.length === 0 ? (
                        <div className="text-center py-12">
                            <div className="text-6xl mb-4">📄</div>
                            <h3 className="text-xl font-semibold mb-2">Chưa có tệp tin nào</h3>
                            <p className="text-gray-600 dark:text-gray-400">
                                Các tệp tin sẽ hiển thị ở đây
                            </p>
                        </div>
                    ) : (
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                            {files.map((file) => (
                                <FileCard key={file.id} file={file} />
                            ))}
                        </div>
                    )}
                </div>
            </div>

            {/* Modals */}
            <FileUploadModal
                isOpen={showFileUpload}
                onClose={() => setShowFileUpload(false)}
                preSelectedMeetingId={meetingId}
            />
        </div>
    );
};

export default MeetingDetail;
