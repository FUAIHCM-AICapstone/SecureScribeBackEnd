'use client';

import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getMyProjects } from '../../services/api/project';
import { getPersonalMeetings } from '../../services/api/meeting';
import { getFiles } from '../../services/api/file';
import { queryKeys } from '../../lib/queryClient';
import { showToast } from '../../hooks/useShowToast';
// Types are inferred from React Query data
import ProjectDetail from './ProjectDetail';
import MeetingDetail from './MeetingDetail';
import ProjectCard from './ProjectCard';
import MeetingCard from './MeetingCard';
import FileCard from './FileCard';
import CreateProjectModal from './CreateProjectModal';
import CreateMeetingModal from './CreateMeetingModal';
import FileUploadModal from './FileUploadModal';
import SearchComponent from './SearchComponent';
import TaskManager from './TaskManager';
import GoogleCalendarSection from './GoogleCalendarSection';


type ViewType = 'dashboard' | 'project' | 'meeting';

const Dashboard: React.FC = () => {
    const [currentView, setCurrentView] = useState<ViewType>('dashboard');
    const [selectedId, setSelectedId] = useState<string>('');

    // Modal states
    const [showCreateProject, setShowCreateProject] = useState(false);
    const [showCreateMeeting, setShowCreateMeeting] = useState(false);
    const [showFileUpload, setShowFileUpload] = useState(false);

    // React Query hooks for data fetching
    const { data: projectsData, isLoading: projectsLoading, error: projectsError } = useQuery({
        queryKey: queryKeys.projects,
        queryFn: () => getMyProjects({ limit: 10 }),
        enabled: currentView === 'dashboard',
    });

    const { data: meetingsData, isLoading: meetingsLoading, error: meetingsError } = useQuery({
        queryKey: queryKeys.personalMeetings,
        queryFn: () => getPersonalMeetings({ limit: 10 }),
        enabled: currentView === 'dashboard',
    });

    const { data: filesData, isLoading: filesLoading, error: filesError } = useQuery({
        queryKey: queryKeys.files,
        queryFn: () => getFiles({ limit: 10 }),
        enabled: currentView === 'dashboard',
    });

    // Show error messages for failed queries
    if (projectsError) {
        console.error('Failed to load projects:', projectsError);
        showToast('error', 'Không thể tải danh sách dự án. Vui lòng thử lại.');
    }
    if (meetingsError) {
        console.error('Failed to load meetings:', meetingsError);
        showToast('error', 'Không thể tải danh sách cuộc họp. Vui lòng thử lại.');
    }
    if (filesError) {
        console.error('Failed to load files:', filesError);
        showToast('error', 'Không thể tải danh sách tệp tin. Vui lòng thử lại.');
    }

    // Extract data from queries
    const projects = projectsData?.data || [];
    const meetings = meetingsData?.data || [];
    const files = filesData?.data || [];

    // Combined loading state
    const loading = projectsLoading || meetingsLoading || filesLoading;

    const handleProjectClick = (projectId: string) => {
        setSelectedId(projectId);
        setCurrentView('project');
    };

    const handleMeetingClick = (meetingId: string) => {
        setSelectedId(meetingId);
        setCurrentView('meeting');
    };

    const handleBackToDashboard = () => {
        setCurrentView('dashboard');
        setSelectedId('');
    };

    if (loading && currentView === 'dashboard') {
        return (
            <div className="flex items-center justify-center min-h-screen">
                <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600"></div>
            </div>
        );
    }

    if (currentView === 'project' && selectedId) {
        return <ProjectDetail projectId={selectedId} onBack={handleBackToDashboard} />;
    }

    if (currentView === 'meeting' && selectedId) {
        return <MeetingDetail meetingId={selectedId} onBack={handleBackToDashboard} />;
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

                {/* Projects Section */}
                <div className="mb-8">
                    <div className="flex justify-between items-center mb-4">
                        <h2 className="text-2xl font-semibold">Dự án</h2>
                        <button
                            onClick={() => setShowCreateProject(true)}
                            className="flex items-center px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md text-sm font-medium"
                        >
                            <span className="mr-2">+</span>
                            Tạo dự án
                        </button>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {projects.map((project) => (
                            <ProjectCard
                                key={project.id}
                                project={project}
                                onClick={() => handleProjectClick(project.id)}
                            />
                        ))}
                    </div>
                </div>

                {/* Meetings Section */}
                <div className="mb-8">
                    <div className="flex justify-between items-center mb-4">
                        <h2 className="text-2xl font-semibold">Cuộc họp cá nhân</h2>
                        <button
                            onClick={() => setShowCreateMeeting(true)}
                            className="flex items-center px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-md text-sm font-medium"
                        >
                            <span className="mr-2">+</span>
                            Tạo cuộc họp
                        </button>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {meetings.map((meeting) => (
                            <MeetingCard
                                key={meeting.id}
                                meeting={meeting}
                                onClick={() => handleMeetingClick(meeting.id)}
                            />
                        ))}
                    </div>
                </div>

                {/* Files Section */}
                <div className="mb-8">
                    <div className="flex justify-between items-center mb-4">
                        <h2 className="text-2xl font-semibold">Tệp tin</h2>
                        <button
                            onClick={() => setShowFileUpload(true)}
                            className="flex items-center px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-md text-sm font-medium"
                        >
                            <span className="mr-2">⬆</span>
                            Tải lên tệp tin
                        </button>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                        {files.map((file) => (
                            <FileCard key={file.id} file={file} />
                        ))}
                    </div>
                </div>

                {/* Search Section */}
                <div className="mb-8">
                    <SearchComponent />
                </div>

                {/* Google Calendar Section */}
                <div className="mb-8">
                    <GoogleCalendarSection />
                </div>

                {/* Tasks Section */}
                <div className="mb-8">
                    <div className="flex justify-between items-center mb-4">
                        <h2 className="text-2xl font-semibold">Nhiệm vụ</h2>
                    </div>
                    <TaskManager />
                </div>
            </div>

            {/* Modals */}
            <CreateProjectModal
                isOpen={showCreateProject}
                onClose={() => setShowCreateProject(false)}
            />

            <CreateMeetingModal
                isOpen={showCreateMeeting}
                onClose={() => setShowCreateMeeting(false)}
            />

            <FileUploadModal
                isOpen={showFileUpload}
                onClose={() => setShowFileUpload(false)}
            />
        </div>
    );
};

export default Dashboard;
