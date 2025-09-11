/* eslint-disable @typescript-eslint/no-unused-vars */
'use client';

import React, { useState, useEffect } from 'react';
import { useMutation, useQueryClient, useQuery } from '@tanstack/react-query';
import { getMyProjects } from '../../services/api/project';
import { getPersonalMeetings } from '../../services/api/meeting';
import { moveFile, deleteFile } from '../../services/api/file';
import { getIndexingStatus } from '../../services/api';
import { queryKeys } from '../../lib/queryClient';
import { showToast } from '../../hooks/useShowToast';
import { useWebSocket, useTaskProgress } from '../../context/WebSocketContext';
import type { FileResponse } from '../../types/file.type';
import type { ProjectResponse } from '../../types/project.type';
import type { MeetingResponse } from '../../types/meeting.type';

// FileCard component for displaying file information with add to project/meeting functionality

interface FileCardProps {
    file: FileResponse;
}

const FileCard: React.FC<FileCardProps> = ({ file }) => {
    const [showAddOptions, setShowAddOptions] = useState(false);
    const [projects, setProjects] = useState<ProjectResponse[]>([]);
    const [meetings, setMeetings] = useState<MeetingResponse[]>([]);
    const [selectedProjectId, setSelectedProjectId] = useState('');
    const [selectedMeetingId, setSelectedMeetingId] = useState('');
    const [hasShownProjectWarning, setHasShownProjectWarning] = useState(false);
    const [hasShownMeetingWarning, setHasShownMeetingWarning] = useState(false);
    const queryClient = useQueryClient();

    // WebSocket for real-time progress updates
    const { isConnected } = useWebSocket();
    const { getCurrentTaskProgress } = useTaskProgress(`index_file_${file.id}`);

    // Debug WebSocket connection
    useEffect(() => {
        console.log(`🔌 FileCard ${file.id} - WebSocket connected:`, isConnected);
    }, [isConnected, file.id]);

    // Query for indexing status
    const { data: indexingStatus, refetch: refetchIndexingStatus } = useQuery({
        queryKey: ['indexing-status', file.id],
        queryFn: () => getIndexingStatus(file.id),
        enabled: !!file.id,
        refetchInterval: (data) => {
            // Refetch every 5 seconds if still indexing
            return (data as any)?.data?.status === 'in_progress' ? 5000 : false;
        },
    });

    // Get current progress from WebSocket or API
    const wsProgress = getCurrentTaskProgress();
    const currentProgress = wsProgress?.progress || indexingStatus?.data?.progress || 0;
    const indexingStatusText = wsProgress?.status || indexingStatus?.data?.status || 'not_started';
    const indexingMessage = wsProgress?.message || indexingStatus?.data?.message || '';

    // Debug progress values
    useEffect(() => {
        console.log(`📊 FileCard ${file.id} progress:`, {
            wsProgress,
            currentProgress,
            indexingStatusText,
            indexingMessage,
            apiStatus: indexingStatus?.data?.status,
            apiProgress: indexingStatus?.data?.progress
        });
    }, [wsProgress, currentProgress, indexingStatusText, indexingMessage, indexingStatus, file.id]);

    // Debug WebSocket progress updates
    useEffect(() => {
        if (wsProgress && wsProgress.progress !== undefined) {
            console.log(`📊 WebSocket progress update for file ${file.id}:`, {
                progress: wsProgress.progress,
                status: wsProgress.status,
                task_type: wsProgress.task_type,
                timestamp: wsProgress.timestamp
            });
        }
    }, [wsProgress, file.id]);

    const loadOptions = async () => {
        try {
            const [projectsData, meetingsData] = await Promise.all([
                getMyProjects({ limit: 20 }),
                getPersonalMeetings({ limit: 20 })
            ]);
            setProjects(projectsData.data);
            setMeetings(meetingsData.data);
        } catch (error) {
            console.error('Failed to load options:', error);
        }
    };

    // Clean up invalid selected IDs when lists change
    useEffect(() => {
        if (selectedProjectId && projects.length > 0 && !hasShownProjectWarning) {
            const projectExists = projects.some(project => project.id === selectedProjectId);
            if (!projectExists) {
                setSelectedProjectId('');
                setHasShownProjectWarning(true);
                // Use setTimeout to avoid showing toast during render
                setTimeout(() => {
                    showToast('warning', 'Dự án đã chọn không còn hợp lệ. Vui lòng chọn lại.');
                }, 100);
            }
        }
    }, [projects, selectedProjectId, hasShownProjectWarning]);

    useEffect(() => {
        if (selectedMeetingId && meetings.length > 0 && !hasShownMeetingWarning) {
            const meetingExists = meetings.some(meeting => meeting.id === selectedMeetingId);
            if (!meetingExists) {
                setSelectedMeetingId('');
                setHasShownMeetingWarning(true);
                // Use setTimeout to avoid showing toast during render
                setTimeout(() => {
                    showToast('warning', 'Cuộc họp đã chọn không còn hợp lệ. Vui lòng chọn lại.');
                }, 100);
            }
        }
    }, [meetings, selectedMeetingId, hasShownMeetingWarning]);

    // Reset warning flags when selections change
    useEffect(() => {
        if (selectedProjectId) {
            setHasShownProjectWarning(false);
        }
    }, [selectedProjectId]);

    useEffect(() => {
        if (selectedMeetingId) {
            setHasShownMeetingWarning(false);
        }
    }, [selectedMeetingId]);

    const addToProjectMutation = useMutation({
        mutationFn: (projectId: string) => moveFile(file.id, { project_id: projectId }),
        onSuccess: () => {
            // Invalidate related queries
            queryClient.invalidateQueries({ queryKey: queryKeys.files });
            queryClient.invalidateQueries({ queryKey: queryKeys.projects });
            setShowAddOptions(false);
            setSelectedProjectId('');
            showToast('success', 'File đã được thêm vào dự án thành công!');
        },
        onError: (error) => {
            console.error('Failed to add file to project:', error);
            showToast('error', 'Không thể thêm file vào dự án. Vui lòng thử lại.');
        },
    });

    const addToMeetingMutation = useMutation({
        mutationFn: (meetingId: string) => moveFile(file.id, { meeting_id: meetingId }),
        onSuccess: () => {
            // Invalidate related queries
            queryClient.invalidateQueries({ queryKey: queryKeys.files });
            queryClient.invalidateQueries({ queryKey: queryKeys.meetings });
            queryClient.invalidateQueries({ queryKey: queryKeys.personalMeetings });
            setShowAddOptions(false);
            setSelectedMeetingId('');
            showToast('success', 'File đã được thêm vào cuộc họp thành công!');
        },
        onError: (error) => {
            console.error('Failed to add file to meeting:', error);
            showToast('error', 'Không thể thêm file vào cuộc họp. Vui lòng thử lại.');
        },
    });

    const deleteFileMutation = useMutation({
        mutationFn: (fileId: string) => deleteFile(fileId),
        onSuccess: () => {
            // Invalidate related queries
            queryClient.invalidateQueries({ queryKey: queryKeys.files });
            queryClient.invalidateQueries({ queryKey: queryKeys.projects });
            queryClient.invalidateQueries({ queryKey: queryKeys.meetings });
            queryClient.invalidateQueries({ queryKey: queryKeys.personalMeetings });
            showToast('success', 'File đã được xóa thành công!');
        },
        onError: (error) => {
            console.error('Failed to delete file:', error);
            showToast('error', 'Có lỗi xảy ra khi xóa file. Vui lòng thử lại.');
        },
    });

    const handleReindexFile = () => {
        showToast('info', 'Chức năng lập chỉ mục lại đã bị xóa');
    };

    const handleAddToProject = () => {
        if (!selectedProjectId) return;

        // Validate that the selected project exists in the fetched projects list
        const projectExists = projects.some(project => project.id === selectedProjectId);
        if (!projectExists) {
            showToast('error', 'Dự án đã chọn không hợp lệ. Vui lòng chọn lại.');
            return;
        }

        addToProjectMutation.mutate(selectedProjectId);
    };

    const handleAddToMeeting = () => {
        if (!selectedMeetingId) return;

        // Validate that the selected meeting exists in the fetched meetings list
        const meetingExists = meetings.some(meeting => meeting.id === selectedMeetingId);
        if (!meetingExists) {
            showToast('error', 'Cuộc họp đã chọn không hợp lệ. Vui lòng chọn lại.');
            return;
        }

        addToMeetingMutation.mutate(selectedMeetingId);
    };

    const handleDeleteFile = () => {
        if (!confirm(`Bạn có chắc chắn muốn xóa file "${file.filename}" không?\n\nHành động này không thể hoàn tác.`)) {
            return;
        }

        deleteFileMutation.mutate(file.id);
    };


    const getIndexingStatusDisplay = () => {
        switch (indexingStatusText) {
            case 'completed':
                return { text: '✅ Đã lập chỉ mục', color: 'text-green-600', icon: '✅' };
            case 'in_progress':
                return { text: '🔄 Đang lập chỉ mục...', color: 'text-blue-600', icon: '🔄' };
            case 'failed':
                return { text: '❌ Lập chỉ mục thất bại', color: 'text-red-600', icon: '❌' };
            default:
                return { text: '⏳ Chưa lập chỉ mục', color: 'text-gray-500', icon: '⏳' };
        }
    };

    const indexingDisplay = getIndexingStatusDisplay();

    const formatFileSize = (bytes: number | null | undefined): string => {
        if (!bytes) return '0 B';
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(1024));
        return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
    };

    const getFileIcon = (mimeType: string | null | undefined): string => {
        if (!mimeType) return '📄';

        if (mimeType.startsWith('image/')) return '🖼️';
        if (mimeType.startsWith('video/')) return '🎥';
        if (mimeType.startsWith('audio/')) return '🎵';
        if (mimeType.includes('pdf')) return '📕';
        if (mimeType.includes('word') || mimeType.includes('document')) return '📝';
        if (mimeType.includes('spreadsheet') || mimeType.includes('excel')) return '📊';
        if (mimeType.includes('presentation') || mimeType.includes('powerpoint')) return '📽️';
        if (mimeType.includes('zip') || mimeType.includes('rar')) return '📦';

        return '📄';
    };

    return (
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4 hover:shadow-md transition-shadow">
            <div className="flex items-start justify-between mb-3">
                <div className="flex items-center space-x-3 flex-1">
                    <div className="text-2xl">
                        {getFileIcon(file.mime_type)}
                    </div>
                    <div className="flex-1 min-w-0">
                        <h4 className="font-medium truncate">
                            {file.filename || 'Tệp không tên'}
                        </h4>
                        <p className="text-sm text-gray-600 dark:text-gray-400 truncate">
                            {file.mime_type || 'Unknown type'}
                        </p>
                    </div>
                </div>
            </div>

            <div className="text-sm text-gray-500 space-y-1 mb-4">
                <div className="flex justify-between">
                    <span>Kích thước:</span>
                    <span>{formatFileSize(file.size_bytes)}</span>
                </div>
                <div className="flex justify-between">
                    <span>Ngày tải lên:</span>
                    <span>{new Date(file.created_at).toLocaleDateString('vi-VN')}</span>
                </div>
                <div className="flex justify-between items-center">
                    <span>Trạng thái:</span>
                    <span className={`flex items-center space-x-1 ${indexingDisplay.color}`}>
                        <span>{indexingDisplay.icon}</span>
                        <span className="text-xs">{indexingDisplay.text}</span>
                    </span>
                </div>
                {indexingStatus?.data?.filename && (
                    <div className="flex justify-between">
                        <span>Tên file:</span>
                        <span className="text-xs text-gray-600 truncate max-w-[120px]" title={indexingStatus.data.filename}>
                            {indexingStatus.data.filename}
                        </span>
                    </div>
                )}
                {indexingStatusText === 'in_progress' && (
                    <div className="mt-2">
                        <div className="flex justify-between text-xs mb-1">
                            <span>Tiến độ lập chỉ mục:</span>
                            <span>{currentProgress}%</span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-2">
                            <div
                                className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                                style={{ width: `${currentProgress}%` }}
                            ></div>
                        </div>
                        {indexingMessage && (
                            <div className="text-xs text-blue-600 mt-1">
                                {indexingMessage}
                            </div>
                        )}
                    </div>
                )}
            </div>

            <div className="flex flex-wrap gap-2">
                <button
                    onClick={() => {
                        setShowAddOptions(!showAddOptions);
                        if (!showAddOptions && (projects.length === 0 || meetings.length === 0)) {
                            loadOptions();
                        }
                    }}
                    className="text-xs bg-blue-600 hover:bg-blue-700 text-white px-2 py-1 rounded"
                >
                    + Thêm vào
                </button>

                {file.storage_url && (
                    <button
                        onClick={() => window.open(file.storage_url!, '_blank')}
                        className="text-xs bg-green-600 hover:bg-green-700 text-white px-2 py-1 rounded"
                    >
                        Tải xuống
                    </button>
                )}

                {/* Indexing-related buttons - Disabled */}
                {indexingStatusText === 'failed' && (
                    <button
                        onClick={handleReindexFile}
                        className="text-xs bg-gray-400 text-white px-2 py-1 rounded cursor-not-allowed"
                        title="Chức năng lập chỉ mục đã bị xóa"
                        disabled
                    >
                        🔄 Lập chỉ mục
                    </button>
                )}

                {indexingStatusText === 'completed' && (
                    <button
                        onClick={handleReindexFile}
                        className="text-xs bg-gray-400 text-white px-2 py-1 rounded cursor-not-allowed"
                        title="Chức năng lập chỉ mục đã bị xóa"
                        disabled
                    >
                        🔄 Cập nhật
                    </button>
                )}

                {indexingStatusText === 'not_started' && (
                    <button
                        onClick={handleReindexFile}
                        className="text-xs bg-gray-400 text-white px-2 py-1 rounded cursor-not-allowed"
                        title="Chức năng lập chỉ mục đã bị xóa"
                        disabled
                    >
                        🚀 Lập chỉ mục
                    </button>
                )}

                <button
                    onClick={handleDeleteFile}
                    disabled={deleteFileMutation.isPending}
                    className="text-xs bg-red-600 hover:bg-red-700 text-white px-2 py-1 rounded disabled:bg-gray-400"
                >
                    {deleteFileMutation.isPending ? '...' : 'Xóa'}
                </button>
            </div>

            {showAddOptions && (
                <div className="mt-3 p-3 bg-gray-50 dark:bg-gray-700 rounded space-y-3">
                    <div>
                        <label htmlFor={`project-select-${file.id}`} className="block text-xs font-medium mb-1">Thêm vào dự án:</label>
                        <select
                            id={`project-select-${file.id}`}
                            value={selectedProjectId}
                            onChange={(e) => setSelectedProjectId(e.target.value)}
                            className="w-full px-2 py-1 border border-gray-300 dark:border-gray-600 rounded text-sm bg-white dark:bg-gray-600"
                        >
                            <option value="">-- Chọn dự án --</option>
                            {projects.map((project) => (
                                <option key={project.id} value={project.id}>
                                    {project.name}
                                </option>
                            ))}
                        </select>
                        <button
                            onClick={handleAddToProject}
                            disabled={addToProjectMutation.isPending || !selectedProjectId}
                            className="mt-1 w-full text-xs bg-green-600 hover:bg-green-700 text-white px-2 py-1 rounded disabled:bg-gray-400"
                        >
                            {addToProjectMutation.isPending ? 'Đang thêm...' : 'Thêm vào dự án'}
                        </button>
                    </div>

                    <div>
                        <label htmlFor={`meeting-select-${file.id}`} className="block text-xs font-medium mb-1">Thêm vào cuộc họp:</label>
                        <select
                            id={`meeting-select-${file.id}`}
                            value={selectedMeetingId}
                            onChange={(e) => setSelectedMeetingId(e.target.value)}
                            className="w-full px-2 py-1 border border-gray-300 dark:border-gray-600 rounded text-sm bg-white dark:bg-gray-600"
                        >
                            <option value="">-- Chọn cuộc họp --</option>
                            {meetings.map((meeting) => (
                                <option key={meeting.id} value={meeting.id}>
                                    {meeting.title || 'Chưa có tiêu đề'}
                                </option>
                            ))}
                        </select>
                        <button
                            onClick={handleAddToMeeting}
                            disabled={addToMeetingMutation.isPending || !selectedMeetingId}
                            className="mt-1 w-full text-xs bg-green-600 hover:bg-green-700 text-white px-2 py-1 rounded disabled:bg-gray-400"
                        >
                            {addToMeetingMutation.isPending ? 'Đang thêm...' : 'Thêm vào cuộc họp'}
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
};

export default FileCard;
