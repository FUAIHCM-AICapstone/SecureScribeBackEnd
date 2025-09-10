'use client';

import React, { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { getMyProjects } from '../../services/api/project';
import { addMeetingToProject as addMeetingToProjectAPI, deleteMeeting } from '../../services/api/meeting';
import { queryKeys } from '../../lib/queryClient';
import { showToast } from '../../hooks/useShowToast';
import type { MeetingResponse } from '../../types/meeting.type';
import type { ProjectResponse } from '../../types/project.type';

// MeetingCard component for displaying meeting information with add to project functionality

interface MeetingCardProps {
    meeting: MeetingResponse;
    onClick: () => void;
}

const MeetingCard: React.FC<MeetingCardProps> = ({ meeting, onClick }) => {
    const [showAddToProject, setShowAddToProject] = useState(false);
    const [projects, setProjects] = useState<ProjectResponse[]>([]);
    const [selectedProjectId, setSelectedProjectId] = useState('');
    const queryClient = useQueryClient();

    const loadProjects = async () => {
        try {
            const response = await getMyProjects({ limit: 20 });
            setProjects(response.data);
        } catch (error) {
            console.error('Failed to load projects:', error);
        }
    };

    const addToProjectMutation = useMutation({
        mutationFn: ({ projectId, meetingId }: { projectId: string; meetingId: string }) =>
            addMeetingToProjectAPI(projectId, meetingId),
        onSuccess: () => {
            // Invalidate related queries
            queryClient.invalidateQueries({ queryKey: queryKeys.meetings });
            queryClient.invalidateQueries({ queryKey: queryKeys.personalMeetings });
            queryClient.invalidateQueries({ queryKey: queryKeys.projects });
            setShowAddToProject(false);
            setSelectedProjectId('');
            showToast('success', 'Cuộc họp đã được thêm vào dự án thành công!');
        },
        onError: (error) => {
            console.error('Failed to add meeting to project:', error);
            showToast('error', 'Không thể thêm cuộc họp vào dự án. Vui lòng thử lại.');
        },
    });

    const deleteMeetingMutation = useMutation({
        mutationFn: (meetingId: string) => deleteMeeting(meetingId),
        onSuccess: () => {
            // Invalidate related queries
            queryClient.invalidateQueries({ queryKey: queryKeys.meetings });
            queryClient.invalidateQueries({ queryKey: queryKeys.personalMeetings });
            queryClient.invalidateQueries({ queryKey: queryKeys.files });
            showToast('success', 'Cuộc họp đã được xóa thành công!');
        },
        onError: (error) => {
            console.error('Failed to delete meeting:', error);
            showToast('error', 'Có lỗi xảy ra khi xóa cuộc họp. Vui lòng thử lại.');
        },
    });

    const handleAddToProject = () => {
        if (!selectedProjectId) return;
        addToProjectMutation.mutate({ projectId: selectedProjectId, meetingId: meeting.id });
    };

    const handleDeleteMeeting = () => {
        if (!confirm(`Bạn có chắc chắn muốn xóa cuộc họp "${meeting.title || 'Chưa có tiêu đề'}" không?\n\nTất cả files liên quan sẽ bị ảnh hưởng. Hành động này không thể hoàn tác.`)) {
            return;
        }

        deleteMeetingMutation.mutate(meeting.id);
    };

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

    return (
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4 hover:shadow-md transition-shadow">
            <div className="flex justify-between items-start mb-3">
                <div
                    className="flex-1 cursor-pointer"
                    onClick={onClick}
                    onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                            e.preventDefault();
                            onClick();
                        }
                    }}
                    role="button"
                    tabIndex={0}
                >
                    <h3 className="font-semibold text-lg">
                        {meeting.title || 'Chưa có tiêu đề'}
                    </h3>
                    <p className="text-gray-600 dark:text-gray-400 text-sm mt-1">
                        {meeting.description || 'Không có mô tả'}
                    </p>
                </div>
                <div className="flex items-center space-x-2">
                    <span className={`px-3 py-1 text-xs rounded-full ${getStatusColor(meeting.status)}`}>
                        {getStatusText(meeting.status)}
                    </span>
                    {meeting.is_personal && (
                        <span className="px-2 py-1 text-xs bg-purple-200 text-purple-600 rounded">
                            Cá nhân
                        </span>
                    )}
                </div>
            </div>

            <div className="flex items-center justify-between text-sm text-gray-500 mb-4">
                <div className="flex items-center space-x-4">
                    {meeting.start_time && (
                        <span>
                            🕐 {new Date(meeting.start_time).toLocaleString('vi-VN')}
                        </span>
                    )}
                    <span>{meeting.projects.length} dự án liên quan</span>
                </div>
                <span>{new Date(meeting.created_at).toLocaleDateString('vi-VN')}</span>
            </div>

            <div className="flex space-x-2">
                <button
                    onClick={() => {
                        setShowAddToProject(!showAddToProject);
                        if (!showAddToProject && projects.length === 0) {
                            loadProjects();
                        }
                    }}
                    className="text-xs bg-blue-600 hover:bg-blue-700 text-white px-2 py-1 rounded"
                >
                    + Thêm vào dự án
                </button>
                <button
                    onClick={(e) => {
                        e.stopPropagation();
                        handleDeleteMeeting();
                    }}
                    disabled={deleteMeetingMutation.isPending}
                    className="text-xs bg-red-600 hover:bg-red-700 text-white px-2 py-1 rounded disabled:bg-gray-400"
                >
                    {deleteMeetingMutation.isPending ? '...' : 'Xóa'}
                </button>
            </div>

            {showAddToProject && (
                <div className="mt-3 p-3 bg-gray-50 dark:bg-gray-700 rounded">
                    <select
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
                        className="mt-2 w-full text-xs bg-green-600 hover:bg-green-700 text-white px-2 py-1 rounded disabled:bg-gray-400"
                    >
                        {addToProjectMutation.isPending ? 'Đang thêm...' : 'Thêm vào dự án'}
                    </button>
                </div>
            )}
        </div>
    );
};

export default MeetingCard;
