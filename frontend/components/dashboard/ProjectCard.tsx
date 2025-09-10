'use client';

import React from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { deleteProject } from '../../services/api/project';
import { queryKeys } from '../../lib/queryClient';
import { showToast } from '../../hooks/useShowToast';
import type { ProjectResponse } from '../../types/project.type';

// ProjectCard component for displaying project information

interface ProjectCardProps {
    project: ProjectResponse;
    onClick: () => void;
}

const ProjectCard: React.FC<ProjectCardProps> = ({ project, onClick }) => {
    const queryClient = useQueryClient();

    const deleteProjectMutation = useMutation({
        mutationFn: (projectId: string) => deleteProject(projectId),
        onSuccess: () => {
            // Invalidate and refetch projects query
            queryClient.invalidateQueries({ queryKey: queryKeys.projects });
            // Invalidate user stats if it exists
            queryClient.invalidateQueries({ queryKey: queryKeys.userStats });
            // Invalidate related meetings and files
            queryClient.invalidateQueries({ queryKey: ['meetings'] });
            queryClient.invalidateQueries({ queryKey: ['files'] });
            showToast('success', 'Dự án đã được xóa thành công!');
        },
        onError: (error) => {
            console.error('Failed to delete project:', error);
            showToast('error', 'Có lỗi xảy ra khi xóa dự án. Vui lòng thử lại.');
        },
    });

    const handleDeleteProject = () => {
        if (!confirm(`Bạn có chắc chắn muốn xóa dự án "${project.name}" không?\n\nTất cả meetings và files liên quan sẽ bị ảnh hưởng. Hành động này không thể hoàn tác.`)) {
            return;
        }

        deleteProjectMutation.mutate(project.id);
    };

    return (
        <div
            className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4 hover:shadow-md transition-shadow cursor-pointer"
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
            <div className="flex justify-between items-start mb-3">
                <h3 className="font-semibold text-lg truncate">{project.name}</h3>
                <span className={`px-2 py-1 text-xs rounded ${project.is_archived
                    ? 'bg-gray-200 text-gray-600'
                    : 'bg-green-200 text-green-600'
                    }`}>
                    {project.is_archived ? 'Đã lưu trữ' : 'Hoạt động'}
                </span>
            </div>

            <p className="text-gray-600 dark:text-gray-400 text-sm mb-4 line-clamp-2">
                {project.description || 'Không có mô tả'}
            </p>

            <div className="flex items-center justify-between text-sm text-gray-500">
                <span>{project.member_count || 0} thành viên</span>
                <span>{new Date(project.created_at).toLocaleDateString('vi-VN')}</span>
            </div>

            <div className="flex justify-end mt-4">
                <button
                    onClick={(e) => {
                        e.stopPropagation();
                        handleDeleteProject();
                    }}
                    disabled={deleteProjectMutation.isPending}
                    className="text-xs bg-red-600 hover:bg-red-700 text-white px-3 py-1 rounded disabled:bg-gray-400"
                >
                    {deleteProjectMutation.isPending ? 'Đang xóa...' : 'Xóa dự án'}
                </button>
            </div>
        </div>
    );
};

export default ProjectCard;
