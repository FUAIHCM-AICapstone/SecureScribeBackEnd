'use client';

import React, { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { createProject } from '../../services/api/project';
import { queryKeys } from '../../lib/queryClient';
import { showToast } from '../../hooks/useShowToast';
import type { ProjectCreate } from '../../types/project.type';

interface CreateProjectModalProps {
    isOpen: boolean;
    onClose: () => void;
}

const CreateProjectModal: React.FC<CreateProjectModalProps> = ({ isOpen, onClose }) => {
    const [formData, setFormData] = useState<ProjectCreate>({
        name: '',
        description: '',
    });
    const [errors, setErrors] = useState<Partial<ProjectCreate>>({});

    const queryClient = useQueryClient();

    const createProjectMutation = useMutation({
        mutationFn: (data: ProjectCreate) => createProject(data),
        onSuccess: () => {
            // Invalidate and refetch projects query
            queryClient.invalidateQueries({ queryKey: queryKeys.projects });

            // Show success message
            showToast('success', 'Dự án đã được tạo thành công!');

            // Reset form and close modal
            setFormData({ name: '', description: '' });
            setErrors({});
            onClose();
        },
        onError: (error) => {
            console.error('Failed to create project:', error);
            showToast('error', 'Không thể tạo dự án. Vui lòng thử lại.');
        },
    });

    const validateForm = (): boolean => {
        const newErrors: Partial<ProjectCreate> = {};

        if (!formData.name?.trim()) {
            newErrors.name = 'Tên dự án là bắt buộc';
        } else if (formData.name.trim().length < 3) {
            newErrors.name = 'Tên dự án phải có ít nhất 3 ký tự';
        } else if (formData.name.trim().length > 100) {
            newErrors.name = 'Tên dự án không được vượt quá 100 ký tự';
        }

        if (formData.description && formData.description.length > 500) {
            newErrors.description = 'Mô tả không được vượt quá 500 ký tự';
        }

        setErrors(newErrors);
        return Object.keys(newErrors).length === 0;
    };

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (validateForm()) {
            createProjectMutation.mutate(formData);
        }
    };

    const handleInputChange = (field: keyof ProjectCreate, value: string) => {
        setFormData(prev => ({ ...prev, [field]: value }));
        // Clear error for this field when user starts typing
        if (errors[field]) {
            setErrors(prev => ({ ...prev, [field]: undefined }));
        }
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white dark:bg-gray-800 rounded-lg p-6 w-full max-w-md mx-4">
                <div className="flex justify-between items-center mb-4">
                    <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                        Tạo dự án mới
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
                        <label htmlFor="project-name" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                            Tên dự án *
                        </label>
                        <input
                            id="project-name"
                            type="text"
                            value={formData.name}
                            onChange={(e) => handleInputChange('name', e.target.value)}
                            className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white ${errors.name ? 'border-red-500' : 'border-gray-300'
                                }`}
                            placeholder="Nhập tên dự án..."
                            disabled={createProjectMutation.isPending}
                        />
                        {errors.name && (
                            <p className="text-red-500 text-xs mt-1">{errors.name}</p>
                        )}
                    </div>

                    <div>
                        <label htmlFor="project-description" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                            Mô tả
                        </label>
                        <textarea
                            id="project-description"
                            value={formData.description}
                            onChange={(e) => handleInputChange('description', e.target.value)}
                            rows={3}
                            className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white resize-none ${errors.description ? 'border-red-500' : 'border-gray-300'
                                }`}
                            placeholder="Mô tả về dự án (tùy chọn)..."
                            disabled={createProjectMutation.isPending}
                        />
                        {errors.description && (
                            <p className="text-red-500 text-xs mt-1">{errors.description}</p>
                        )}
                        {formData.description && (
                            <p className="text-gray-500 text-xs mt-1">
                                {formData.description.length}/500 ký tự
                            </p>
                        )}
                    </div>

                    <div className="flex justify-end space-x-3 pt-4">
                        <button
                            type="button"
                            onClick={onClose}
                            className="px-4 py-2 text-gray-600 hover:text-gray-800 dark:text-gray-400 dark:hover:text-gray-200"
                            disabled={createProjectMutation.isPending}
                        >
                            Hủy
                        </button>
                        <button
                            type="submit"
                            disabled={createProjectMutation.isPending || !formData.name?.trim()}
                            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center"
                        >
                            {createProjectMutation.isPending ? (
                                <>
                                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                                    Đang tạo...
                                </>
                            ) : (
                                'Tạo dự án'
                            )}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};

export default CreateProjectModal;
