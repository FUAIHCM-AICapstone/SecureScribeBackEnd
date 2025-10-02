'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import React, { useEffect, useMemo, useState } from 'react';
import { showToast } from '../../hooks/useShowToast';
import { queryKeys } from '../../lib/queryClient';
import { getTask, updateTask } from '../../services/api/task';
import { getUsers } from '../../services/api/user';
import type { TaskStatus, TaskUpdate } from '../../types/task.type';

interface EditTaskModalProps {
    taskId: string | null;
    isOpen: boolean;
    onClose: () => void;
}

const EditTaskModal: React.FC<EditTaskModalProps> = ({ taskId, isOpen, onClose }) => {
    const queryClient = useQueryClient();
    const [local, setLocal] = useState<TaskUpdate>({});
    const [errors, setErrors] = useState<{ title?: string; due_date?: string; reminder_at?: string }>();

    const { data: task, isLoading } = useQuery({
        queryKey: taskId ? queryKeys.task(taskId) : ['tasks', 'none'],
        queryFn: () => getTask(taskId as string),
        enabled: isOpen && !!taskId,
    });

    const { data: usersPaginated } = useQuery({
        queryKey: ['users', 'list-for-assignee'],
        queryFn: () => getUsers({ limit: 100 }),
        enabled: isOpen,
    });
    const users = useMemo(() => usersPaginated?.data || [], [usersPaginated?.data]);

    const toLocalInput = (value?: string) => {
        if (!value) return '';
        const d = new Date(value);
        if (Number.isNaN(d.getTime())) return '';
        const pad = (n: number) => String(n).padStart(2, '0');
        return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
    };

    useEffect(() => {
        if (task) {
            setLocal({
                title: task.title,
                description: task.description,
                assignee_id: task.assignee_id,
                status: task.status as TaskStatus,
                due_date: toLocalInput(task.due_date),
                reminder_at: toLocalInput(task.reminder_at),
            });
        }
    }, [task]);

    const validate = (): boolean => {
        const next: typeof errors = {};
        if (local.title !== undefined && !local.title.trim()) next.title = 'Tiêu đề là bắt buộc';
        if (local.due_date && isNaN(new Date(local.due_date).getTime())) next.due_date = 'Ngày đến hạn không hợp lệ';
        if (local.reminder_at && isNaN(new Date(local.reminder_at).getTime())) next.reminder_at = 'Thời gian nhắc không hợp lệ';
        setErrors(next);
        return Object.keys(next).length === 0;
    };

    const toIso = (value?: string) => {
        if (!value) return undefined;
        const d = new Date(value);
        return Number.isNaN(d.getTime()) ? undefined : d.toISOString();
    };

    const mutation = useMutation({
        mutationFn: ({ id, updates }: { id: string; updates: TaskUpdate }) => updateTask(id, updates),
        onSuccess: () => {
            if (taskId) queryClient.invalidateQueries({ queryKey: queryKeys.task(taskId) });
            queryClient.invalidateQueries({ queryKey: queryKeys.tasks });
            showToast('success', 'Cập nhật nhiệm vụ thành công!');
            onClose();
        },
        onError: (error) => {
            console.error('Update task error', error);
            showToast('error', 'Không thể cập nhật nhiệm vụ. Vui lòng thử lại.');
        },
    });

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (!taskId) return;
        if (!validate()) return;
        const updates: TaskUpdate = {
            title: local.title?.trim(),
            description: local.description?.trim(),
            assignee_id: local.assignee_id || undefined,
            status: local.status,
            due_date: toIso(local.due_date),
            reminder_at: toIso(local.reminder_at),
        };
        mutation.mutate({ id: taskId, updates });
    };

    const setField = (key: keyof TaskUpdate, value: any) => {
        setLocal(prev => ({ ...prev, [key]: value }));
        if (errors && errors[key as keyof typeof errors]) {
            setErrors(prev => ({ ...prev, [key as keyof typeof errors]: undefined }));
        }
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white dark:bg-gray-800 rounded-lg p-6 w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto">
                <div className="flex justify-between items-center mb-4">
                    <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Chỉnh sửa nhiệm vụ</h2>
                    <button onClick={onClose} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300">✕</button>
                </div>

                {isLoading ? (
                    <div className="text-sm text-gray-500">Đang tải...</div>
                ) : (
                    <form onSubmit={handleSubmit} className="space-y-4">
                        <div>
                            <label htmlFor="task-title" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Tiêu đề</label>
                            <input
                                id="task-title"
                                type="text"
                                value={local.title || ''}
                                onChange={(e) => setField('title', e.target.value)}
                                className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white ${errors?.title ? 'border-red-500' : 'border-gray-300'}`}
                                placeholder="Nhập tiêu đề..."
                                disabled={mutation.isPending}
                            />
                            {errors?.title && <p className="text-red-500 text-xs mt-1">{errors.title}</p>}
                        </div>

                        <div>
                            <label htmlFor="task-description" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Mô tả</label>
                            <textarea
                                id="task-description"
                                value={local.description || ''}
                                onChange={(e) => setField('description', e.target.value)}
                                rows={3}
                                className="w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white resize-none"
                                placeholder="Mô tả..."
                                disabled={mutation.isPending}
                            />
                        </div>

                        <div>
                            <label htmlFor="task-status" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Trạng thái</label>
                            <select
                                id="task-status"
                                value={local.status || 'todo'}
                                onChange={(e) => setField('status', e.target.value as TaskStatus)}
                                className="w-full px-3 py-2 border rounded-md dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                                disabled={mutation.isPending}
                            >
                                <option value="todo">Todo</option>
                                <option value="in_progress">In Progress</option>
                                <option value="done">Done</option>
                            </select>
                        </div>

                        <div>
                            <label htmlFor="task-assignee" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Người được giao</label>
                            <select
                                id="task-assignee"
                                value={local.assignee_id || ''}
                                onChange={(e) => setField('assignee_id', e.target.value || undefined)}
                                className="w-full px-3 py-2 border rounded-md dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                                disabled={mutation.isPending}
                            >
                                <option value="">-- Không chỉ định --</option>
                                {users.map((u: any) => (
                                    <option key={u.id} value={u.id}>{u.name || u.email}</option>
                                ))}
                            </select>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <label htmlFor="task-due-date" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Hạn chót</label>
                                <input
                                    id="task-due-date"
                                    type="datetime-local"
                                    value={local.due_date || ''}
                                    onChange={(e) => setField('due_date', e.target.value)}
                                    className="w-full px-3 py-2 border rounded-md dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                                    disabled={mutation.isPending}
                                />
                                {errors?.due_date && <p className="text-red-500 text-xs mt-1">{errors.due_date}</p>}
                            </div>
                            <div>
                                <label htmlFor="task-reminder" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Nhắc nhở lúc</label>
                                <input
                                    id="task-reminder"
                                    type="datetime-local"
                                    value={local.reminder_at || ''}
                                    onChange={(e) => setField('reminder_at', e.target.value)}
                                    className="w-full px-3 py-2 border rounded-md dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                                    disabled={mutation.isPending}
                                />
                                {errors?.reminder_at && <p className="text-red-500 text-xs mt-1">{errors.reminder_at}</p>}
                            </div>
                        </div>

                        <div className="flex justify-end space-x-3 pt-4">
                            <button
                                type="button"
                                onClick={onClose}
                                className="px-4 py-2 text-gray-600 hover:text-gray-800 dark:text-gray-400 dark:hover:text-gray-200"
                                disabled={mutation.isPending}
                            >
                                Hủy
                            </button>
                            <button type="submit" disabled={mutation.isPending} className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center">
                                {mutation.isPending ? (
                                    <>
                                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                                        Đang lưu...
                                    </>
                                ) : 'Lưu thay đổi'}
                            </button>
                        </div>
                    </form>
                )}
            </div>
        </div>
    );
};

export default EditTaskModal;


