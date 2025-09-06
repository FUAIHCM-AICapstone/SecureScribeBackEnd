'use client';

import React, { useState, useEffect } from 'react';
import {
    getMeetings,
    createMeeting,
    updateMeeting,
    deleteMeeting,
    completeMeeting,
    cancelMeeting
} from '../../services/api/meeting';
import type { MeetingResponse, MeetingCreate, MeetingUpdate } from '../../types/meeting.type';
import Button from '../ui/Button';
import { Skeleton } from '../ui/Skeleton';

const MeetingManager: React.FC = () => {
    const [meetings, setMeetings] = useState<MeetingResponse[]>([]);
    const [loading, setLoading] = useState(true);
    const [showCreateModal, setShowCreateModal] = useState(false);
    const [editingMeeting, setEditingMeeting] = useState<MeetingResponse | null>(null);
    const [formData, setFormData] = useState<MeetingCreate>({
        title: '',
        description: '',
        url: '',
        start_time: '',
        is_personal: false,
        project_ids: []
    });
    const [submitting, setSubmitting] = useState(false);

    useEffect(() => {
        loadMeetings();
    }, []);

    const loadMeetings = async () => {
        try {
            setLoading(true);
            const response = await getMeetings({ limit: 50 });
            setMeetings(response.data);
        } catch (error) {
            console.error('Failed to load meetings:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleCreateMeeting = async () => {
        try {
            setSubmitting(true);
            await createMeeting(formData);
            setShowCreateModal(false);
            resetForm();
            loadMeetings();
        } catch (error) {
            console.error('Failed to create meeting:', error);
        } finally {
            setSubmitting(false);
        }
    };

    const handleUpdateMeeting = async () => {
        if (!editingMeeting) return;

        try {
            setSubmitting(true);
            const updates: MeetingUpdate = {
                title: formData.title,
                description: formData.description,
                url: formData.url,
                start_time: formData.start_time,
            };
            await updateMeeting(editingMeeting.id, updates);
            setEditingMeeting(null);
            resetForm();
            loadMeetings();
        } catch (error) {
            console.error('Failed to update meeting:', error);
        } finally {
            setSubmitting(false);
        }
    };

    const handleDeleteMeeting = async (meetingId: string) => {
        if (!confirm('Bạn có chắc chắn muốn xóa cuộc họp này?')) return;

        try {
            await deleteMeeting(meetingId);
            loadMeetings();
        } catch (error) {
            console.error('Failed to delete meeting:', error);
        }
    };

    const handleStatusChange = async (meeting: MeetingResponse, newStatus: string) => {
        try {
            if (newStatus === 'completed') {
                await completeMeeting(meeting.id);
            } else if (newStatus === 'cancelled') {
                await cancelMeeting(meeting.id);
            }
            loadMeetings();
        } catch (error) {
            console.error('Failed to update meeting status:', error);
        }
    };

    const resetForm = () => {
        setFormData({
            title: '',
            description: '',
            url: '',
            start_time: '',
            is_personal: false,
            project_ids: []
        });
    };

    const openEditModal = (meeting: MeetingResponse) => {
        setEditingMeeting(meeting);
        setFormData({
            title: meeting.title || '',
            description: meeting.description || '',
            url: meeting.url || '',
            start_time: meeting.start_time || '',
            is_personal: meeting.is_personal,
            project_ids: []
        });
    };

    const closeModal = () => {
        setShowCreateModal(false);
        setEditingMeeting(null);
        resetForm();
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

    if (loading) {
        return (
            <div className="p-6">
                <div className="flex justify-between items-center mb-6">
                    <h2 className="text-2xl font-bold">Quản lý cuộc họp</h2>
                    <Skeleton width={120} height={40} />
                </div>
                <div className="space-y-4">
                    {Array.from({ length: 5 }).map((_, i) => (
                        <div key={i} className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
                            <div className="flex justify-between items-start mb-2">
                                <Skeleton height={24} width="60%" />
                                <Skeleton width={80} height={24} />
                            </div>
                            <Skeleton height={16} width="40%" className="mb-2" />
                            <Skeleton height={16} width="30%" className="mb-4" />
                            <div className="flex space-x-2">
                                <Skeleton width={80} height={32} />
                                <Skeleton width={80} height={32} />
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
                <h2 className="text-2xl font-bold">Quản lý cuộc họp</h2>
                <Button
                    onClick={() => setShowCreateModal(true)}
                    className="bg-blue-600 hover:bg-blue-700 text-white"
                >
                    + Tạo cuộc họp mới
                </Button>
            </div>

            {meetings.length === 0 ? (
                <div className="text-center py-12">
                    <div className="text-6xl mb-4">📅</div>
                    <h3 className="text-xl font-semibold mb-2">Chưa có cuộc họp nào</h3>
                    <p className="text-gray-600 dark:text-gray-400 mb-6">
                        Tạo cuộc họp đầu tiên của bạn
                    </p>
                    <Button
                        onClick={() => setShowCreateModal(true)}
                        className="bg-blue-600 hover:bg-blue-700 text-white"
                    >
                        Tạo cuộc họp đầu tiên
                    </Button>
                </div>
            ) : (
                <div className="space-y-4">
                    {meetings.map((meeting) => (
                        <div key={meeting.id} className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4 hover:shadow-md transition-shadow">
                            <div className="flex justify-between items-start mb-3">
                                <div className="flex-1">
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
                                    {meeting.url && (
                                        <span>
                                            🔗 <a href={meeting.url} target="_blank" rel="noopener noreferrer"
                                                className="text-blue-600 hover:underline">Link họp</a>
                                        </span>
                                    )}
                                    <span>{meeting.projects.length} dự án liên quan</span>
                                </div>
                                <span>{new Date(meeting.created_at).toLocaleDateString('vi-VN')}</span>
                            </div>

                            <div className="flex space-x-2">
                                <Button
                                    onClick={() => openEditModal(meeting)}
                                    className="bg-gray-600 hover:bg-gray-700 text-white text-sm"
                                >
                                    Chỉnh sửa
                                </Button>

                                {meeting.status === 'active' && (
                                    <>
                                        <Button
                                            onClick={() => handleStatusChange(meeting, 'completed')}
                                            className="bg-blue-600 hover:bg-blue-700 text-white text-sm"
                                        >
                                            Hoàn thành
                                        </Button>
                                        <Button
                                            onClick={() => handleStatusChange(meeting, 'cancelled')}
                                            className="bg-yellow-600 hover:bg-yellow-700 text-white text-sm"
                                        >
                                            Hủy
                                        </Button>
                                    </>
                                )}

                                <Button
                                    onClick={() => handleDeleteMeeting(meeting.id)}
                                    className="bg-red-600 hover:bg-red-700 text-white text-sm"
                                >
                                    Xóa
                                </Button>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {/* Create/Edit Modal */}
            {(showCreateModal || editingMeeting) && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                    <div className="bg-white dark:bg-gray-800 rounded-lg p-6 w-full max-w-lg">
                        <h3 className="text-xl font-semibold mb-4">
                            {editingMeeting ? 'Chỉnh sửa cuộc họp' : 'Tạo cuộc họp mới'}
                        </h3>

                        <div className="space-y-4">
                            <div>
                                <label htmlFor="meeting-title" className="block text-sm font-medium mb-1">Tiêu đề *</label>
                                <input
                                    id="meeting-title"
                                    type="text"
                                    value={formData.title}
                                    onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700"
                                    placeholder="Nhập tiêu đề cuộc họp"
                                />
                            </div>

                            <div>
                                <label htmlFor="meeting-description" className="block text-sm font-medium mb-1">Mô tả</label>
                                <textarea
                                    id="meeting-description"
                                    value={formData.description}
                                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 h-20 resize-none"
                                    placeholder="Nhập mô tả cuộc họp (không bắt buộc)"
                                />
                            </div>

                            <div>
                                <label htmlFor="meeting-url" className="block text-sm font-medium mb-1">Link họp</label>
                                <input
                                    id="meeting-url"
                                    type="url"
                                    value={formData.url}
                                    onChange={(e) => setFormData({ ...formData, url: e.target.value })}
                                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700"
                                    placeholder="https://meet.google.com/..."
                                />
                            </div>

                            <div>
                                <label htmlFor="meeting-start-time" className="block text-sm font-medium mb-1">Thời gian bắt đầu</label>
                                <input
                                    id="meeting-start-time"
                                    type="datetime-local"
                                    value={formData.start_time}
                                    onChange={(e) => setFormData({ ...formData, start_time: e.target.value })}
                                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700"
                                />
                            </div>

                            <div>
                                <label className="flex items-center">
                                    <input
                                        type="checkbox"
                                        checked={formData.is_personal}
                                        onChange={(e) => setFormData({ ...formData, is_personal: e.target.checked })}
                                        className="mr-2"
                                    />
                                    <span className="text-sm font-medium">Cuộc họp cá nhân</span>
                                </label>
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
                                onClick={editingMeeting ? handleUpdateMeeting : handleCreateMeeting}
                                className="flex-1 bg-blue-600 hover:bg-blue-700 text-white"
                                disabled={submitting || !formData.title?.trim()}
                            >
                                {submitting ? 'Đang xử lý...' : editingMeeting ? 'Cập nhật' : 'Tạo'}
                            </Button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default MeetingManager;
