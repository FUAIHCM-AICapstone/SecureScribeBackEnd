'use client';

import React, { useState, useEffect, useMemo } from 'react';
import { useMutation, useQueryClient, useQuery } from '@tanstack/react-query';
import { createMeeting } from '../../services/api/meeting';
import { getMyProjects } from '../../services/api/project';
import { queryKeys } from '../../lib/queryClient';
import { showToast } from '../../hooks/useShowToast';
import type { MeetingCreate } from '../../types/meeting.type';
// Types are inferred from React Query data

interface CreateMeetingModalProps {
    isOpen: boolean;
    onClose: () => void;
    preSelectedProjectId?: string;
}

const CreateMeetingModal: React.FC<CreateMeetingModalProps> = ({
    isOpen,
    onClose,
    preSelectedProjectId
}) => {
    const [formData, setFormData] = useState<MeetingCreate>({
        title: '',
        description: '',
        url: '',
        start_time: '',
        is_personal: false,
        project_ids: [],
    });
    const [errors, setErrors] = useState<{
        title?: string;
        description?: string;
        url?: string;
        start_time?: string;
        project_ids?: string;
    }>({});

    const queryClient = useQueryClient();

    // Fetch projects for the dropdown
    const { data: projectsData, isLoading: projectsLoading } = useQuery({
        queryKey: queryKeys.projects,
        queryFn: () => getMyProjects({ limit: 50 }),
        enabled: isOpen,
    });

    const projects = useMemo(() => projectsData?.data || [], [projectsData?.data]);

    // Update project_ids when preSelectedProjectId changes
    useEffect(() => {
        if (preSelectedProjectId) {
            setFormData(prev => ({
                ...prev,
                project_ids: [preSelectedProjectId],
                is_personal: false,
            }));
        }
    }, [preSelectedProjectId]);

    // Clean up invalid project_ids when projects list changes
    useEffect(() => {
        if (projects.length > 0) {
            setFormData(prev => ({
                ...prev,
                project_ids: prev.project_ids.filter(projectId =>
                    projects.some(project => project.id === projectId)
                ),
            }));
        }
    }, [projects]);

    const createMeetingMutation = useMutation({
        mutationFn: (data: MeetingCreate) => createMeeting(data),
        onSuccess: () => {
            // Invalidate related queries
            queryClient.invalidateQueries({ queryKey: queryKeys.meetings });
            queryClient.invalidateQueries({ queryKey: queryKeys.personalMeetings });
            queryClient.invalidateQueries({ queryKey: queryKeys.projects });

            // Show success message
            showToast('success', 'Cuộc họp đã được tạo thành công!');

            // Reset form and close modal
            setFormData({
                title: '',
                description: '',
                url: '',
                start_time: '',
                is_personal: false,
                project_ids: [],
            });
            setErrors({});
            onClose();
        },
        onError: (error) => {
            console.error('Failed to create meeting:', error);
            showToast('error', 'Không thể tạo cuộc họp. Vui lòng thử lại.');
        },
    });

    const validateForm = (): boolean => {
        const newErrors: Partial<typeof errors> = {};

        if (!formData.title?.trim()) {
            newErrors.title = 'Tiêu đề cuộc họp là bắt buộc';
        } else if (formData.title.trim().length < 3) {
            newErrors.title = 'Tiêu đề phải có ít nhất 3 ký tự';
        } else if (formData.title.trim().length > 200) {
            newErrors.title = 'Tiêu đề không được vượt quá 200 ký tự';
        }

        if (formData.description && formData.description.length > 1000) {
            newErrors.description = 'Mô tả không được vượt quá 1000 ký tự';
        }

        if (formData.url && formData.url.trim()) {
            const urlPattern = /^https?:\/\/.+/;
            if (!urlPattern.test(formData.url)) {
                newErrors.url = 'URL không hợp lệ';
            }
        }

        if (formData.start_time && formData.start_time.trim()) {
            const startTime = new Date(formData.start_time);
            if (isNaN(startTime.getTime())) {
                newErrors.start_time = 'Thời gian không hợp lệ';
            } else if (startTime <= new Date()) {
                newErrors.start_time = 'Thời gian bắt đầu phải sau thời điểm hiện tại';
            }
        }

        // Validate project_ids - check if selected projects exist in fetched list
        if (!formData.is_personal) {
            if (formData.project_ids.length === 0) {
                newErrors.project_ids = 'Vui lòng chọn ít nhất một dự án';
            } else {
                // Check if all selected project ids exist in the fetched projects list
                const invalidProjectIds = formData.project_ids.filter(projectId =>
                    !projects.some(project => project.id === projectId)
                );
                if (invalidProjectIds.length > 0) {
                    newErrors.project_ids = 'Một số dự án đã chọn không hợp lệ';
                }
            }
        }

        setErrors(newErrors);
        return Object.keys(newErrors).length === 0;
    };

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (validateForm()) {
            createMeetingMutation.mutate(formData);
        }
    };

    const handleTextInputChange = (field: 'title' | 'description' | 'url' | 'start_time', value: string) => {
        setFormData(prev => ({ ...prev, [field]: value }));
        clearError(field);
    };

    const handleCheckboxChange = (field: 'is_personal', value: boolean) => {
        setFormData(prev => ({ ...prev, [field]: value }));
        clearError('project_ids'); // Clear project_ids error when switching between personal and non-personal
    };

    const clearError = (fieldName: keyof typeof errors) => {
        if (errors[fieldName]) {
            setErrors(prev => ({ ...prev, [fieldName]: undefined }));
        }
    };

    const handleProjectChange = (projectId: string, checked: boolean) => {
        // Validate that the projectId exists in the fetched projects list
        const projectExists = projects.some(project => project.id === projectId);

        if (!projectExists) {
            console.warn(`Invalid project ID selected: ${projectId}`);
            return;
        }

        if (checked) {
            setFormData(prev => ({
                ...prev,
                project_ids: [...new Set([...prev.project_ids, projectId])], // Use Set to avoid duplicates
            }));
        } else {
            setFormData(prev => ({
                ...prev,
                project_ids: prev.project_ids.filter(id => id !== projectId),
            }));
        }
        clearError('project_ids');
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white dark:bg-gray-800 rounded-lg p-6 w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto">
                <div className="flex justify-between items-center mb-4">
                    <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                        Tạo cuộc họp mới
                    </h2>
                    <button
                        onClick={onClose}
                        className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                    >
                        ✕
                    </button>
                </div>

                <form onSubmit={handleSubmit} className="space-y-4">
                    <div>
                        <label htmlFor="meeting-title" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                            Tiêu đề cuộc họp *
                        </label>
                        <input
                            id="meeting-title"
                            type="text"
                            value={formData.title}
                            onChange={(e) => handleTextInputChange('title', e.target.value)}
                            className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white ${errors.title ? 'border-red-500' : 'border-gray-300'}`}
                            placeholder="Nhập tiêu đề cuộc họp..."
                            disabled={createMeetingMutation.isPending}
                        />
                        {errors.title && (
                            <p className="text-red-500 text-xs mt-1">{errors.title}</p>
                        )}
                    </div>

                    <div>
                        <label htmlFor="meeting-description" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                            Mô tả
                        </label>
                        <textarea
                            id="meeting-description"
                            value={formData.description}
                            onChange={(e) => handleTextInputChange('description', e.target.value)}
                            rows={3}
                            className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white resize-none ${errors.description ? 'border-red-500' : 'border-gray-300'}`}
                            placeholder="Mô tả về cuộc họp (tùy chọn)..."
                            disabled={createMeetingMutation.isPending}
                        />
                        {errors.description && (
                            <p className="text-red-500 text-xs mt-1">{errors.description}</p>
                        )}
                        {formData.description && (
                            <p className="text-gray-500 text-xs mt-1">
                                {formData.description.length}/1000 ký tự
                            </p>
                        )}
                    </div>

                    <div>
                        <label htmlFor="meeting-url" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                            Link họp
                        </label>
                        <input
                            id="meeting-url"
                            type="url"
                            value={formData.url}
                            onChange={(e) => handleTextInputChange('url', e.target.value)}
                            className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white ${errors.url ? 'border-red-500' : 'border-gray-300'}`}
                            placeholder="https://..."
                            disabled={createMeetingMutation.isPending}
                        />
                        {errors.url && (
                            <p className="text-red-500 text-xs mt-1">{errors.url}</p>
                        )}
                    </div>

                    <div>
                        <label htmlFor="meeting-start-time" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                            Thời gian bắt đầu
                        </label>
                        <input
                            id="meeting-start-time"
                            type="datetime-local"
                            value={formData.start_time}
                            onChange={(e) => handleTextInputChange('start_time', e.target.value)}
                            className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white ${errors.start_time ? 'border-red-500' : 'border-gray-300'}`}
                            disabled={createMeetingMutation.isPending}
                        />
                        {errors.start_time && (
                            <p className="text-red-500 text-xs mt-1">{errors.start_time}</p>
                        )}
                    </div>

                    <div>
                        <label className="flex items-center">
                            <input
                                type="checkbox"
                                checked={formData.is_personal}
                                onChange={(e) => handleCheckboxChange('is_personal', e.target.checked)}
                                className="mr-2"
                                disabled={createMeetingMutation.isPending}
                            />
                            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                                Cuộc họp cá nhân
                            </span>
                        </label>
                        <p className="text-xs text-gray-500 mt-1">
                            {formData.is_personal
                                ? 'Cuộc họp cá nhân chỉ hiển thị với bạn'
                                : 'Cuộc họp sẽ được chia sẻ với các dự án được chọn'
                            }
                        </p>
                    </div>

                    {!formData.is_personal && (
                        <div>
                            <label htmlFor="project-checkboxes" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                Chọn dự án liên quan *
                            </label>
                            {projectsLoading ? (
                                <div className="text-sm text-gray-500">Đang tải danh sách dự án...</div>
                            ) : projects.length === 0 ? (
                                <div className="text-sm text-gray-500">Không có dự án nào. Tạo dự án trước khi tạo cuộc họp.</div>
                            ) : (
                                <div id="project-checkboxes" className="space-y-2 max-h-32 overflow-y-auto">
                                    {projects.map((project) => (
                                        <label key={project.id} className="flex items-center">
                                            <input
                                                type="checkbox"
                                                checked={formData.project_ids.includes(project.id)}
                                                onChange={(e) => handleProjectChange(project.id, e.target.checked)}
                                                className="mr-2"
                                                disabled={createMeetingMutation.isPending}
                                            />
                                            <span className="text-sm text-gray-700 dark:text-gray-300">
                                                {project.name}
                                            </span>
                                        </label>
                                    ))}
                                </div>
                            )}
                            {errors.project_ids && (
                                <p className="text-red-500 text-xs mt-1">{errors.project_ids}</p>
                            )}
                        </div>
                    )}

                    <div className="flex justify-end space-x-3 pt-4">
                        <button
                            type="button"
                            onClick={onClose}
                            className="px-4 py-2 text-gray-600 hover:text-gray-800 dark:text-gray-400 dark:hover:text-gray-200"
                            disabled={createMeetingMutation.isPending}
                        >
                            Hủy
                        </button>
                        <button
                            type="submit"
                            disabled={createMeetingMutation.isPending || !formData.title?.trim()}
                            className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-md disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center"
                        >
                            {createMeetingMutation.isPending ? (
                                <>
                                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                                    Đang tạo...
                                </>
                            ) : (
                                'Tạo cuộc họp'
                            )}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};

export default CreateMeetingModal;
