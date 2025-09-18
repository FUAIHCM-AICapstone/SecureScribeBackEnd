'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import React, { useEffect, useMemo, useState } from 'react';
import { showToast } from '../../hooks/useShowToast';
import { queryKeys } from '../../lib/queryClient';
import { getPersonalMeetings, getProjectMeetings } from '../../services/api/meeting';
import { getMyProjects } from '../../services/api/project';
import { createTask } from '../../services/api/task';
import { getUsers } from '../../services/api/user';
import type { TaskCreate } from '../../types/task.type';

interface CreateTaskModalProps {
    isOpen: boolean;
    onClose: () => void;
}

const DEFAULT_LIMIT = 50;

const CreateTaskModal: React.FC<CreateTaskModalProps> = ({ isOpen, onClose }) => {
    const [formData, setFormData] = useState<TaskCreate>({
        title: '',
        description: '',
        assignee_id: undefined,
        meeting_id: undefined,
        project_ids: [],
        due_date: '',
        reminder_at: '',
    });

    const [errors, setErrors] = useState<{
        title?: string;
        assignee_id?: string;
        project_ids?: string;
        meeting_id?: string;
        due_date?: string;
        reminder_at?: string;
    }>({});

    const queryClient = useQueryClient();

    // Fetch supporting data
    const { data: projectsData, isLoading: projectsLoading } = useQuery({
        queryKey: queryKeys.projects,
        queryFn: () => getMyProjects({ limit: DEFAULT_LIMIT }),
        enabled: isOpen,
    });
    const projects = useMemo(() => projectsData?.data || [], [projectsData?.data]);

    const { data: personalMeetingsData, isLoading: personalMeetingsLoading } = useQuery({
        queryKey: queryKeys.personalMeetings,
        queryFn: () => getPersonalMeetings({ limit: DEFAULT_LIMIT }),
        enabled: isOpen,
    });
    const personalMeetings = useMemo(() => personalMeetingsData?.data || [], [personalMeetingsData?.data]);

    // Meetings for selected projects
    const [projectMeetings, setProjectMeetings] = useState<Record<string, any[]>>({});
    useEffect(() => {
        if (!isOpen) return;
        const loadMeetings = async () => {
            const entries = await Promise.all(
                (formData.project_ids || []).map(async (pid) => {
                    try {
                        const resp = await getProjectMeetings(pid, { limit: DEFAULT_LIMIT });
                        return [pid, resp.data] as const;
                    } catch (e) {
                        console.warn('Failed to load meetings for project', pid, e);
                        return [pid, []] as const;
                    }
                })
            );
            const map: Record<string, any[]> = {};
            entries.forEach(([pid, arr]) => { map[pid] = Array.isArray(arr) ? [...arr] : []; });
            setProjectMeetings(map);
        };
        loadMeetings();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [isOpen, JSON.stringify(formData.project_ids)]);

    const { data: usersPaginated, isLoading: usersLoading } = useQuery({
        queryKey: ['users', 'list-for-assignee'],
        queryFn: () => getUsers({ limit: DEFAULT_LIMIT }),
        enabled: isOpen,
    });
    const users = useMemo(() => usersPaginated?.data || [], [usersPaginated?.data]);

    // Combine meetings (personal + from selected projects) - must be declared before any early returns
    const allMeetings = useMemo(() => {
        const projectMeetingsFlat = Object.values(projectMeetings).flat();
        return [...personalMeetings, ...projectMeetingsFlat];
    }, [personalMeetings, projectMeetings]);

    const createMutation = useMutation({
        mutationFn: (data: TaskCreate) => createTask(data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: queryKeys.tasks });
            showToast('success', 'Tạo nhiệm vụ thành công!');
            resetAndClose();
        },
        onError: (error) => {
            console.error('Create task error', error);
            showToast('error', 'Không thể tạo nhiệm vụ. Vui lòng thử lại.');
        },
    });

    const resetAndClose = () => {
        setFormData({
            title: '',
            description: '',
            assignee_id: undefined,
            meeting_id: undefined,
            project_ids: [],
            due_date: '',
            reminder_at: '',
        });
        setErrors({});
        onClose();
    };

    const validate = (): boolean => {
        const next: typeof errors = {};
        if (!formData.title?.trim()) next.title = 'Tiêu đề là bắt buộc';
        if (!Array.isArray(formData.project_ids)) formData.project_ids = [];
        // Allow both meeting and projects simultaneously per requirement
        if (formData.due_date && isNaN(new Date(formData.due_date).getTime())) next.due_date = 'Ngày đến hạn không hợp lệ';
        if (formData.reminder_at && isNaN(new Date(formData.reminder_at).getTime())) next.reminder_at = 'Thời gian nhắc không hợp lệ';
        setErrors(next);
        return Object.keys(next).length === 0;
    };

    const toIso = (value?: string) => {
        if (!value) return undefined;
        const d = new Date(value);
        return Number.isNaN(d.getTime()) ? undefined : d.toISOString();
    };

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (!validate()) return;

        const payload: TaskCreate = {
            title: formData.title.trim(),
            description: formData.description?.trim() || undefined,
            assignee_id: formData.assignee_id || undefined,
            meeting_id: formData.meeting_id || undefined,
            project_ids: formData.project_ids || [],
            due_date: toIso(formData.due_date),
            reminder_at: toIso(formData.reminder_at),
        };
        createMutation.mutate(payload);
    };

    const setField = (key: keyof TaskCreate, value: any) => {
        setFormData(prev => ({ ...prev, [key]: value }));
        if (errors[key as keyof typeof errors]) {
            setErrors(prev => ({ ...prev, [key as keyof typeof errors]: undefined }));
        }
    };

    if (!isOpen) return null;

    const isPending = createMutation.isPending;

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white dark:bg-gray-800 rounded-lg p-6 w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto">
                <div className="flex justify-between items-center mb-4">
                    <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Tạo nhiệm vụ mới</h2>
                    <button onClick={resetAndClose} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300">✕</button>
                </div>

                <form onSubmit={handleSubmit} className="space-y-4">
                    <div>
                        <label htmlFor="task-title" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Tiêu đề *</label>
                        <input
                            id="task-title"
                            type="text"
                            value={formData.title}
                            onChange={(e) => setField('title', e.target.value)}
                            className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white ${errors.title ? 'border-red-500' : 'border-gray-300'}`}
                            placeholder="Nhập tiêu đề..."
                            disabled={isPending}
                        />
                        {errors.title && <p className="text-red-500 text-xs mt-1">{errors.title}</p>}
                    </div>

                    <div>
                        <label htmlFor="task-desc" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Mô tả</label>
                        <textarea
                            id="task-desc"
                            value={formData.description}
                            onChange={(e) => setField('description', e.target.value)}
                            rows={3}
                            className="w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white resize-none"
                            placeholder="Mô tả (tùy chọn)..."
                            disabled={isPending}
                        />
                    </div>

                    <div>
                        <label htmlFor="task-assignee" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Người được giao</label>
                        {usersLoading ? (
                            <div className="text-sm text-gray-500">Đang tải người dùng...</div>
                        ) : (
                            <select
                                id="task-assignee"
                                value={formData.assignee_id || ''}
                                onChange={(e) => setField('assignee_id', e.target.value || undefined)}
                                className="w-full px-3 py-2 border rounded-md dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                                disabled={isPending}
                            >
                                <option value="">-- Không chỉ định --</option>
                                {users.map((u: any) => (
                                    <option key={u.id} value={u.id}>{u.name || u.email}</option>
                                ))}
                            </select>
                        )}
                    </div>

                    <div>
                        <p className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Dự án liên quan</p>
                        {projectsLoading ? (
                            <div className="text-sm text-gray-500">Đang tải dự án...</div>
                        ) : projects.length === 0 ? (
                            <div className="text-sm text-gray-500">Không có dự án. Tạo dự án trước.</div>
                        ) : (
                            <div className="space-y-2 max-h-32 overflow-y-auto">
                                {projects.map((p: any) => (
                                    <label key={p.id} className="flex items-center">
                                        <input
                                            type="checkbox"
                                            className="mr-2"
                                            checked={formData.project_ids.includes(p.id)}
                                            onChange={(e) => {
                                                const checked = e.target.checked;
                                                setFormData(prev => ({
                                                    ...prev,
                                                    project_ids: checked
                                                        ? [...new Set([...prev.project_ids, p.id])]
                                                        : prev.project_ids.filter(id => id !== p.id)
                                                }));
                                            }}
                                            disabled={isPending}
                                        />
                                        <span className="text-sm text-gray-700 dark:text-gray-300">{p.name}</span>
                                    </label>
                                ))}
                            </div>
                        )}
                        {errors.project_ids && <p className="text-red-500 text-xs mt-1">{errors.project_ids}</p>}
                    </div>

                    <div>
                        <label htmlFor="task-meeting" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Cuộc họp liên quan</label>
                        {personalMeetingsLoading ? (
                            <div className="text-sm text-gray-500">Đang tải cuộc họp...</div>
                        ) : (
                            <select
                                id="task-meeting"
                                value={formData.meeting_id || ''}
                                onChange={(e) => setField('meeting_id', e.target.value || undefined)}
                                className="w-full px-3 py-2 border rounded-md dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                                disabled={isPending}
                            >
                                <option value="">-- Không chọn --</option>
                                {allMeetings.map((m: any) => (
                                    <option key={m.id} value={m.id}>{m.title || m.id}</option>
                                ))}
                            </select>
                        )}
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                            <label htmlFor="task-due" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Hạn chót</label>
                            <input
                                id="task-due"
                                type="datetime-local"
                                value={formData.due_date || ''}
                                onChange={(e) => setField('due_date', e.target.value)}
                                className="w-full px-3 py-2 border rounded-md dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                                disabled={isPending}
                            />
                            {errors.due_date && <p className="text-red-500 text-xs mt-1">{errors.due_date}</p>}
                        </div>
                        <div>
                            <label htmlFor="task-rem" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Nhắc nhở lúc</label>
                            <input
                                id="task-rem"
                                type="datetime-local"
                                value={formData.reminder_at || ''}
                                onChange={(e) => setField('reminder_at', e.target.value)}
                                className="w-full px-3 py-2 border rounded-md dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                                disabled={isPending}
                            />
                            {errors.reminder_at && <p className="text-red-500 text-xs mt-1">{errors.reminder_at}</p>}
                        </div>
                    </div>

                    <div className="flex justify-end space-x-3 pt-4">
                        <button
                            type="button"
                            onClick={resetAndClose}
                            className="px-4 py-2 text-gray-600 hover:text-gray-800 dark:text-gray-400 dark:hover:text-gray-200"
                            disabled={isPending}
                        >Hủy</button>
                        <button
                            type="submit"
                            disabled={isPending || !formData.title?.trim()}
                            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center"
                        >
                            {isPending ? (
                                <>
                                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                                    Đang tạo...
                                </>
                            ) : 'Tạo nhiệm vụ'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};

export default CreateTaskModal;


