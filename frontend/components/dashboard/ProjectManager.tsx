'use client';

import React, { useState, useEffect } from 'react';
import {
    getMyProjects,
    createProject,
    updateProject,
    deleteProject,
    archiveProject,
    unarchiveProject
} from '../../services/api/project';
import type { ProjectResponse, ProjectCreate, ProjectUpdate } from '../../types/project.type';
import Button from '../ui/Button';
import { Skeleton } from '../ui/Skeleton';

const ProjectManager: React.FC = () => {
    const [projects, setProjects] = useState<ProjectResponse[]>([]);
    const [loading, setLoading] = useState(true);
    const [showCreateModal, setShowCreateModal] = useState(false);
    const [editingProject, setEditingProject] = useState<ProjectResponse | null>(null);
    const [formData, setFormData] = useState<ProjectCreate>({ name: '', description: '' });
    const [submitting, setSubmitting] = useState(false);

    useEffect(() => {
        loadProjects();
    }, []);

    const loadProjects = async () => {
        try {
            setLoading(true);
            const response = await getMyProjects({ limit: 50 });
            setProjects(response.data);
        } catch (error) {
            console.error('Failed to load projects:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleCreateProject = async () => {
        try {
            setSubmitting(true);
            await createProject(formData);
            setShowCreateModal(false);
            setFormData({ name: '', description: '' });
            loadProjects();
        } catch (error) {
            console.error('Failed to create project:', error);
        } finally {
            setSubmitting(false);
        }
    };

    const handleUpdateProject = async () => {
        if (!editingProject) return;

        try {
            setSubmitting(true);
            const updates: ProjectUpdate = {
                name: formData.name,
                description: formData.description,
            };
            await updateProject(editingProject.id, updates);
            setEditingProject(null);
            setFormData({ name: '', description: '' });
            loadProjects();
        } catch (error) {
            console.error('Failed to update project:', error);
        } finally {
            setSubmitting(false);
        }
    };

    const handleDeleteProject = async (projectId: string) => {
        if (!confirm('Bạn có chắc chắn muốn xóa dự án này?')) return;

        try {
            await deleteProject(projectId);
            loadProjects();
        } catch (error) {
            console.error('Failed to delete project:', error);
        }
    };

    const handleToggleArchive = async (project: ProjectResponse) => {
        try {
            if (project.is_archived) {
                await unarchiveProject(project.id);
            } else {
                await archiveProject(project.id);
            }
            loadProjects();
        } catch (error) {
            console.error('Failed to toggle archive status:', error);
        }
    };

    const openEditModal = (project: ProjectResponse) => {
        setEditingProject(project);
        setFormData({
            name: project.name,
            description: project.description || '',
        });
    };

    const closeModal = () => {
        setShowCreateModal(false);
        setEditingProject(null);
        setFormData({ name: '', description: '' });
    };

    if (loading) {
        return (
            <div className="p-6">
                <div className="flex justify-between items-center mb-6">
                    <h2 className="text-2xl font-bold">Quản lý dự án</h2>
                    <Skeleton width={120} height={40} />
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {Array.from({ length: 6 }).map((_, i) => (
                        <div key={i} className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
                            <Skeleton height={24} className="mb-2" />
                            <Skeleton height={16} width="75%" className="mb-4" />
                            <div className="flex space-x-2">
                                <Skeleton width={60} height={32} />
                                <Skeleton width={60} height={32} />
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        );
    }

    return (
        <div className="p-6">
            <div className="flex justify-between items-center mb-6">
                <h2 className="text-2xl font-bold">Quản lý dự án</h2>
                <Button
                    onClick={() => setShowCreateModal(true)}
                    className="bg-blue-600 hover:bg-blue-700 text-white"
                >
                    + Tạo dự án mới
                </Button>
            </div>

            {projects.length === 0 ? (
                <div className="text-center py-12">
                    <div className="text-6xl mb-4">📁</div>
                    <h3 className="text-xl font-semibold mb-2">Chưa có dự án nào</h3>
                    <p className="text-gray-600 dark:text-gray-400 mb-6">
                        Tạo dự án đầu tiên của bạn để bắt đầu
                    </p>
                    <Button
                        onClick={() => setShowCreateModal(true)}
                        className="bg-blue-600 hover:bg-blue-700 text-white"
                    >
                        Tạo dự án đầu tiên
                    </Button>
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {projects.map((project) => (
                        <div key={project.id} className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4 hover:shadow-md transition-shadow">
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

                            <div className="flex items-center justify-between text-sm text-gray-500 mb-4">
                                <span>{project.member_count || 0} thành viên</span>
                                <span>{new Date(project.created_at).toLocaleDateString('vi-VN')}</span>
                            </div>

                            <div className="flex space-x-2">
                                <Button
                                    onClick={() => openEditModal(project)}
                                    className="flex-1 bg-gray-600 hover:bg-gray-700 text-white text-sm"
                                >
                                    Chỉnh sửa
                                </Button>
                                <Button
                                    onClick={() => handleToggleArchive(project)}
                                    className={`flex-1 text-sm ${project.is_archived
                                        ? 'bg-green-600 hover:bg-green-700'
                                        : 'bg-yellow-600 hover:bg-yellow-700'
                                        } text-white`}
                                >
                                    {project.is_archived ? 'Khôi phục' : 'Lưu trữ'}
                                </Button>
                                <Button
                                    onClick={() => handleDeleteProject(project.id)}
                                    className="flex-1 bg-red-600 hover:bg-red-700 text-white text-sm"
                                >
                                    Xóa
                                </Button>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {/* Create/Edit Modal */}
            {(showCreateModal || editingProject) && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                    <div className="bg-white dark:bg-gray-800 rounded-lg p-6 w-full max-w-md">
                        <h3 className="text-xl font-semibold mb-4">
                            {editingProject ? 'Chỉnh sửa dự án' : 'Tạo dự án mới'}
                        </h3>

                        <div className="space-y-4">
                            <div>
                                <label htmlFor="project-name" className="block text-sm font-medium mb-1">Tên dự án *</label>
                                <input
                                    id="project-name"
                                    type="text"
                                    value={formData.name}
                                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700"
                                    placeholder="Nhập tên dự án"
                                />
                            </div>

                            <div>
                                <label htmlFor="project-description" className="block text-sm font-medium mb-1">Mô tả</label>
                                <textarea
                                    id="project-description"
                                    value={formData.description}
                                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 h-24 resize-none"
                                    placeholder="Nhập mô tả dự án (không bắt buộc)"
                                />
                            </div>
                        </div>

                        <div className="flex space-x-3 mt-6">
                            <Button
                                onClick={closeModal}
                                className="flex-1 bg-gray-600 hover:bg-gray-700 text-white"
                                disabled={submitting}
                            >
                                Hủy
                            </Button>
                            <Button
                                onClick={editingProject ? handleUpdateProject : handleCreateProject}
                                className="flex-1 bg-blue-600 hover:bg-blue-700 text-white"
                                disabled={submitting || !formData.name.trim()}
                            >
                                {submitting ? 'Đang xử lý...' : editingProject ? 'Cập nhật' : 'Tạo'}
                            </Button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default ProjectManager;
