'use client';

import React, { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { queryKeys } from '../../lib/queryClient';
import { getTasks, bulkDeleteTasks, bulkUpdateTasks } from '../../services/api/task';
import type { TaskResponse, TaskStatus, BulkTaskUpdate } from '../../types/task.type';
import { showToast } from '../../hooks/useShowToast';
import CreateTaskModal from './CreateTaskModal';
import EditTaskModal from './EditTaskModal';

const DEFAULT_LIMIT = 20;

const TaskManager: React.FC = () => {
    const queryClient = useQueryClient();
    const [page, setPage] = useState(1);
    const [limit] = useState(DEFAULT_LIMIT);
    const [titleFilter, setTitleFilter] = useState('');
    const [statusFilter, setStatusFilter] = useState<TaskStatus | ''>('');
    const [selected, setSelected] = useState<Set<string>>(new Set());
    const [createOpen, setCreateOpen] = useState(false);
    const [editTaskId, setEditTaskId] = useState<string | null>(null);

    const { data: tasksData, isLoading, error } = useQuery({
        queryKey: [queryKeys.tasks[0], { page, limit, title: titleFilter, status: statusFilter }],
        queryFn: () => getTasks(
            { title: titleFilter || undefined, status: statusFilter || undefined },
            { page, limit }
        ),
        placeholderData: (previousData) => previousData, // Keep previous data while loading new data
    });

    const tasks = useMemo(() => {
        const list: TaskResponse[] = tasksData?.data || [];
        // Sort by created_at desc for display
        return [...list].sort((a, b) => (new Date(b.created_at).getTime() - new Date(a.created_at).getTime()));
    }, [tasksData?.data]);

    const pagination = tasksData?.pagination || { page, limit, total: 0, total_pages: 0 };

    useEffect(() => {
        if (error) {
            console.error('Load tasks error', error);
            showToast('error', 'Không thể tải nhiệm vụ. Vui lòng thử lại.');
        }
    }, [error]);

    const bulkDeleteMutation = useMutation({
        mutationFn: (ids: string[]) => bulkDeleteTasks(ids),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: queryKeys.tasks });
            setSelected(new Set());
            showToast('success', 'Đã xóa nhiệm vụ đã chọn');
        },
        onError: (e) => {
            console.error('Bulk delete error', e);
            showToast('error', 'Không thể xóa nhiệm vụ.');
        }
    });

    const bulkStatusMutation = useMutation({
        mutationFn: ({ ids, status }: { ids: string[]; status: TaskStatus }) => {
            const payload: BulkTaskUpdate = {
                tasks: ids.map(id => ({ id, updates: { status } }))
            };
            return bulkUpdateTasks(payload);
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: queryKeys.tasks });
            setSelected(new Set());
            showToast('success', 'Đã cập nhật trạng thái');
        },
        onError: (e) => {
            console.error('Bulk update error', e);
            showToast('error', 'Không thể cập nhật trạng thái.');
        }
    });

    const toggleSelect = (id: string) => {
        setSelected(prev => {
            const next = new Set(prev);
            if (next.has(id)) next.delete(id); else next.add(id);
            return next;
        });
    };

    const allSelected = tasks.length > 0 && selected.size === tasks.length;
    const toggleSelectAll = () => {
        if (allSelected) setSelected(new Set());
        else setSelected(new Set(tasks.map(t => t.id)));
    };

    return (
        <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow">
            <div className="flex justify-between items-center mb-4">
                <h3 className="text-xl font-semibold">Nhiệm vụ</h3>
                <div className="flex gap-2">
                    <button onClick={() => setCreateOpen(true)} className="px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md text-sm">+ Tạo nhiệm vụ</button>
                    <div className="relative">
                        <select
                            onChange={(e) => {
                                const val = e.target.value as TaskStatus | '';
                                if (!val) return;
                                bulkStatusMutation.mutate({ ids: Array.from(selected), status: val as TaskStatus });
                            }}
                            value=""
                            className="px-3 py-2 border rounded-md text-sm dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                            disabled={selected.size === 0 || bulkStatusMutation.isPending}
                        >
                            <option value="">Cập nhật trạng thái...</option>
                            <option value="todo">Todo</option>
                            <option value="in_progress">In Progress</option>
                            <option value="done">Done</option>
                        </select>
                    </div>
                    <button
                        onClick={() => bulkDeleteMutation.mutate(Array.from(selected))}
                        disabled={selected.size === 0 || bulkDeleteMutation.isPending}
                        className="px-3 py-2 bg-red-600 hover:bg-red-700 text-white rounded-md text-sm disabled:bg-gray-400 disabled:cursor-not-allowed"
                    >
                        Xóa đã chọn
                    </button>
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-4">
                <input
                    type="text"
                    placeholder="Tìm theo tiêu đề..."
                    value={titleFilter}
                    onChange={(e) => setTitleFilter(e.target.value)}
                    className="px-3 py-2 border rounded-md dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                />
                <select
                    value={statusFilter}
                    onChange={(e) => setStatusFilter(e.target.value as TaskStatus | '')}
                    className="px-3 py-2 border rounded-md dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                >
                    <option value="">Tất cả trạng thái</option>
                    <option value="todo">Todo</option>
                    <option value="in_progress">In Progress</option>
                    <option value="done">Done</option>
                </select>
                <div className="flex items-center justify-end text-sm text-gray-500">
                    {isLoading ? 'Đang tải...' : `Tổng: ${pagination.total}`}
                </div>
            </div>

            <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                    <thead className="bg-gray-50 dark:bg-gray-700">
                        <tr>
                            <th className="px-4 py-2"><input type="checkbox" checked={allSelected} onChange={toggleSelectAll} /></th>
                            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Tiêu đề</th>
                            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Trạng thái</th>
                            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Người được giao</th>
                            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Hạn chót</th>
                            <th className="px-4 py-2"></th>
                        </tr>
                    </thead>
                    <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                        {tasks.map((t) => (
                            <tr key={t.id}>
                                <td className="px-4 py-2"><input type="checkbox" checked={selected.has(t.id)} onChange={() => toggleSelect(t.id)} /></td>
                                <td className="px-4 py-2">
                                    <div className="font-medium text-gray-900 dark:text-gray-100">{t.title}</div>
                                    {t.description && <div className="text-xs text-gray-500 line-clamp-1">{t.description}</div>}
                                </td>
                                <td className="px-4 py-2">
                                    <span className="inline-flex items-center px-2 py-1 rounded text-xs bg-gray-100 dark:bg-gray-700">
                                        {t.status}
                                    </span>
                                </td>
                                <td className="px-4 py-2">{t.assignee?.name || t.assignee?.email || '-'}</td>
                                <td className="px-4 py-2">{t.due_date ? new Date(t.due_date).toLocaleString() : '-'}</td>
                                <td className="px-4 py-2 text-right">
                                    <button onClick={() => setEditTaskId(t.id)} className="px-2 py-1 text-sm text-blue-600 hover:underline">Sửa</button>
                                </td>
                            </tr>
                        ))}
                        {!isLoading && tasks.length === 0 && (
                            <tr>
                                <td className="px-4 py-6 text-center text-sm text-gray-500" colSpan={6}>Không có nhiệm vụ</td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>

            <div className="flex items-center justify-between mt-4">
                <div className="text-sm text-gray-500">Trang {pagination.page}/{pagination.total_pages || 1}</div>
                <div className="flex gap-2">
                    <button
                        onClick={() => setPage(p => Math.max(1, p - 1))}
                        disabled={pagination.page <= 1}
                        className="px-3 py-2 border rounded-md text-sm disabled:opacity-50"
                    >Trước</button>
                    <button
                        onClick={() => setPage(p => p + 1)}
                        disabled={pagination.page >= (pagination.total_pages || 1)}
                        className="px-3 py-2 border rounded-md text-sm disabled:opacity-50"
                    >Sau</button>
                </div>
            </div>

            <CreateTaskModal isOpen={createOpen} onClose={() => setCreateOpen(false)} />
            <EditTaskModal isOpen={!!editTaskId} taskId={editTaskId} onClose={() => setEditTaskId(null)} />
        </div>
    );
};

export default TaskManager;


