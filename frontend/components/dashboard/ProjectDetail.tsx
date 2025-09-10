'use client';

import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getProject } from '../../services/api/project';
import { getProjectMeetings } from '../../services/api/meeting';
import { getProjectFiles } from '../../services/api/file';
import { queryKeys } from '../../lib/queryClient';
import { showToast } from '../../hooks/useShowToast';
// Types are inferred from React Query data
import MeetingCard from './MeetingCard';
import FileCard from './FileCard';
import CreateMeetingModal from './CreateMeetingModal';
import FileUploadModal from './FileUploadModal';

// ProjectDetail component for displaying project meetings and files

interface ProjectDetailProps {
    projectId: string;
    onBack: () => void;
}

const ProjectDetail: React.FC<ProjectDetailProps> = ({ projectId, onBack }) => {
    const [activeTab, setActiveTab] = useState<'meetings' | 'files'>('meetings');

    // Modal states
    const [showCreateMeeting, setShowCreateMeeting] = useState(false);
    const [showFileUpload, setShowFileUpload] = useState(false);

    // React Query hooks for data fetching
    const { data: projectData, isLoading: projectLoading, error: projectError } = useQuery({
        queryKey: queryKeys.project(projectId),
        queryFn: () => getProject(projectId, true),
    });

    const { data: meetingsData, isLoading: meetingsLoading, error: meetingsError } = useQuery({
        queryKey: queryKeys.projectMeetings(projectId),
        queryFn: () => getProjectMeetings(projectId, { limit: 20 }),
        enabled: activeTab === 'meetings',
    });

    const { data: filesData, isLoading: filesLoading, error: filesError } = useQuery({
        queryKey: queryKeys.projectFiles(projectId),
        queryFn: () => getProjectFiles(projectId, { limit: 20 }),
        enabled: activeTab === 'files',
    });

    // Show error messages for failed queries
    if (projectError) {
        console.error('Failed to load project:', projectError);
        showToast('error', 'Không thể tải thông tin dự án. Vui lòng thử lại.');
    }
    if (meetingsError) {
        console.error('Failed to load meetings:', meetingsError);
        showToast('error', 'Không thể tải danh sách cuộc họp. Vui lòng thử lại.');
    }
    if (filesError) {
        console.error('Failed to load files:', filesError);
        showToast('error', 'Không thể tải danh sách tệp tin. Vui lòng thử lại.');
    }

    // Extract data from queries
    const project = projectData || null;
    const meetings = meetingsData?.data || [];
    const files = filesData?.data || [];

    // Combined loading state
    const loading = projectLoading || (activeTab === 'meetings' ? meetingsLoading : filesLoading);

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-screen">
                <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600"></div>
            </div>
        );
    }

    if (!project) {
        return (
            <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                    <div className="text-center">
                        <h1 className="text-2xl font-bold mb-4">Không tìm thấy dự án</h1>
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
                        {project.name}
                    </h1>
                    <p className="text-gray-600 dark:text-gray-400">
                        {project.description || 'Không có mô tả'}
                    </p>
                    <div className="flex items-center space-x-4 mt-4 text-sm text-gray-500">
                        <span>{project.members?.length || 0} thành viên</span>
                        <span>Trạng thái: {project.is_archived ? 'Đã lưu trữ' : 'Hoạt động'}</span>
                        <span>Tạo ngày: {new Date(project.created_at).toLocaleDateString('vi-VN')}</span>
                    </div>
                </div>

                {/* Navigation Tabs */}
                <div className="mb-6">
                    <nav className="flex space-x-1 bg-white dark:bg-gray-800 p-1 rounded-lg shadow-sm">
                        <button
                            onClick={() => setActiveTab('meetings')}
                            className={`flex items-center px-4 py-2 rounded-md text-sm font-medium transition-colors ${activeTab === 'meetings'
                                ? 'bg-blue-600 text-white'
                                : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                                }`}
                        >
                            Cuộc họp ({meetings.length})
                        </button>
                        <button
                            onClick={() => setActiveTab('files')}
                            className={`flex items-center px-4 py-2 rounded-md text-sm font-medium transition-colors ${activeTab === 'files'
                                ? 'bg-blue-600 text-white'
                                : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                                }`}
                        >
                            Tệp tin ({files.length})
                        </button>
                    </nav>
                </div>

                {/* Content */}
                <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6">
                    {activeTab === 'meetings' && (
                        <div>
                            <div className="flex justify-between items-center mb-6">
                                <h2 className="text-2xl font-semibold">Cuộc họp trong dự án</h2>
                                <button
                                    onClick={() => setShowCreateMeeting(true)}
                                    className="flex items-center px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-md text-sm font-medium"
                                >
                                    <span className="mr-2">+</span>
                                    Tạo cuộc họp
                                </button>
                            </div>
                            {meetings.length === 0 ? (
                                <div className="text-center py-12">
                                    <div className="text-6xl mb-4">📅</div>
                                    <h3 className="text-xl font-semibold mb-2">Chưa có cuộc họp nào</h3>
                                    <p className="text-gray-600 dark:text-gray-400">
                                        Các cuộc họp sẽ hiển thị ở đây
                                    </p>
                                </div>
                            ) : (
                                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                                    {meetings.map((meeting) => (
                                        <MeetingCard
                                            key={meeting.id}
                                            meeting={meeting}
                                            onClick={() => {
                                                // TODO: Navigate to meeting detail
                                                console.log('Navigate to meeting:', meeting.id);
                                            }}
                                        />
                                    ))}
                                </div>
                            )}
                        </div>
                    )}

                    {activeTab === 'files' && (
                        <div>
                            <div className="flex justify-between items-center mb-6">
                                <h2 className="text-2xl font-semibold">Tệp tin trong dự án</h2>
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
                    )}
                </div>
            </div>

            {/* Modals */}
            <CreateMeetingModal
                isOpen={showCreateMeeting}
                onClose={() => setShowCreateMeeting(false)}
                preSelectedProjectId={projectId}
            />

            <FileUploadModal
                isOpen={showFileUpload}
                onClose={() => setShowFileUpload(false)}
                preSelectedProjectId={projectId}
            />
        </div>
    );
};

export default ProjectDetail;
