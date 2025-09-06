'use client';

import React, { useState, useEffect } from 'react';
import { getMyProjects, getMyProjectStats } from '../../services/api/project';
import { getMeetings } from '../../services/api/meeting';
import { getFiles } from '../../services/api/file';
import type { ProjectResponse, ProjectStats } from '../../types/project.type';
import type { MeetingResponse } from '../../types/meeting.type';
import type { FileResponse } from '../../types/file.type';
import ProjectManager from './ProjectManager';
import DashboardStats from './DashboardStats';
import MeetingManager from './MeetingManager';
import FileManager from './FileManager';


type TabType = 'overview' | 'projects' | 'meetings' | 'files';

const Dashboard: React.FC = () => {
    const [activeTab, setActiveTab] = useState<TabType>('overview');
    const [loading, setLoading] = useState(true);
    const [stats, setStats] = useState<ProjectStats | null>(null);
    const [projects, setProjects] = useState<ProjectResponse[]>([]);
    const [meetings, setMeetings] = useState<MeetingResponse[]>([]);
    const [files, setFiles] = useState<FileResponse[]>([]);

    useEffect(() => {
        loadDashboardData();
    }, []);

    const loadDashboardData = async () => {
        try {
            setLoading(true);
            const [statsData, projectsData, meetingsData, filesData] = await Promise.all([
                getMyProjectStats(),
                getMyProjects({ limit: 5 }),
                getMeetings({ limit: 5 }),
                getFiles({ limit: 5 })
            ]);

            setStats(statsData);
            setProjects(projectsData.data);
            setMeetings(meetingsData.data);
            setFiles(filesData.data);
        } catch (error) {
            console.error('Failed to load dashboard data:', error);
        } finally {
            setLoading(false);
        }
    };

    const tabs = [
        { id: 'overview' as TabType, label: 'Tổng quan', icon: '📊' },
        { id: 'projects' as TabType, label: 'Dự án', icon: '📁' },
        { id: 'meetings' as TabType, label: 'Cuộc họp', icon: '📅' },
        { id: 'files' as TabType, label: 'Tệp tin', icon: '📄' },
    ];

    const renderContent = () => {
        switch (activeTab) {
            case 'overview':
                return (
                    <div className="space-y-6">
                        <DashboardStats stats={stats} />
                        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6">
                                <h3 className="text-lg font-semibold mb-4">Dự án gần đây</h3>
                                <div className="space-y-3">
                                    {projects.slice(0, 3).map((project) => (
                                        <div key={project.id} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700 rounded">
                                            <div>
                                                <p className="font-medium">{project.name}</p>
                                                <p className="text-sm text-gray-500">{project.description}</p>
                                            </div>
                                            <span className={`px-2 py-1 text-xs rounded ${project.is_archived
                                                ? 'bg-gray-200 text-gray-600'
                                                : 'bg-green-200 text-green-600'
                                                }`}>
                                                {project.is_archived ? 'Đã lưu trữ' : 'Hoạt động'}
                                            </span>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6">
                                <h3 className="text-lg font-semibold mb-4">Cuộc họp sắp tới</h3>
                                <div className="space-y-3">
                                    {meetings.slice(0, 3).map((meeting) => (
                                        <div key={meeting.id} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700 rounded">
                                            <div>
                                                <p className="font-medium">{meeting.title || 'Chưa có tiêu đề'}</p>
                                                <p className="text-sm text-gray-500">
                                                    {meeting.start_time ? new Date(meeting.start_time).toLocaleDateString('vi-VN') : 'Chưa có thời gian'}
                                                </p>
                                            </div>
                                            <span className={`px-2 py-1 text-xs rounded ${meeting.status === 'active'
                                                ? 'bg-green-200 text-green-600'
                                                : meeting.status === 'completed'
                                                    ? 'bg-blue-200 text-blue-600'
                                                    : 'bg-gray-200 text-gray-600'
                                                }`}>
                                                {meeting.status === 'active' ? 'Hoạt động' :
                                                    meeting.status === 'completed' ? 'Hoàn thành' : 'Đã hủy'}
                                            </span>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6">
                                <h3 className="text-lg font-semibold mb-4">Tệp tin gần đây</h3>
                                <div className="space-y-3">
                                    {files.slice(0, 3).map((file) => (
                                        <div key={file.id} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700 rounded">
                                            <div>
                                                <p className="font-medium">{file.filename || 'Tệp không tên'}</p>
                                                <p className="text-sm text-gray-500">{file.mime_type}</p>
                                            </div>
                                            <span className="text-sm text-gray-500">
                                                {(file.size_bytes || 0) / 1024 / 1024 < 1
                                                    ? `${Math.round((file.size_bytes || 0) / 1024)} KB`
                                                    : `${((file.size_bytes || 0) / 1024 / 1024).toFixed(1)} MB`
                                                }
                                            </span>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </div>
                    </div>
                );

            case 'projects':
                return <ProjectManager />;

            case 'meetings':
                return <MeetingManager />;

            case 'files':
                return <FileManager />;

            default:
                return null;
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-screen">
                <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600"></div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <div className="mb-8">
                    <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
                        Dashboard
                    </h1>
                    <p className="text-gray-600 dark:text-gray-400">
                        Quản lý dự án, cuộc họp và tệp tin của bạn
                    </p>
                </div>

                {/* Navigation Tabs */}
                <div className="mb-6">
                    <nav className="flex space-x-1 bg-white dark:bg-gray-800 p-1 rounded-lg shadow-sm">
                        {tabs.map((tab) => (
                            <button
                                key={tab.id}
                                onClick={() => setActiveTab(tab.id)}
                                className={`flex items-center px-4 py-2 rounded-md text-sm font-medium transition-colors ${activeTab === tab.id
                                    ? 'bg-blue-600 text-white'
                                    : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                                    }`}
                            >
                                <span className="mr-2">{tab.icon}</span>
                                {tab.label}
                            </button>
                        ))}
                    </nav>
                </div>

                {/* Content */}
                <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm">
                    {renderContent()}
                </div>
            </div>
        </div>
    );
};

export default Dashboard;
