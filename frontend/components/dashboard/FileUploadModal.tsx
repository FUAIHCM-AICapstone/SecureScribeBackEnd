'use client';

import React, { useState, useCallback, useRef, useMemo } from 'react';
import { useMutation, useQueryClient, useQuery } from '@tanstack/react-query';
import { uploadFile } from '../../services/api/file';
import { getMyProjects } from '../../services/api/project';
import { getPersonalMeetings } from '../../services/api/meeting';
import { queryKeys } from '../../lib/queryClient';
import { showToast } from '../../hooks/useShowToast';
import type { FileUploadData } from '../../types/file.type';
// Types are inferred from React Query data

interface FileUploadModalProps {
    isOpen: boolean;
    onClose: () => void;
    preSelectedProjectId?: string;
    preSelectedMeetingId?: string;
}

interface UploadFile {
    file: File;
    id: string;
    progress: number;
    status: 'pending' | 'uploading' | 'completed' | 'error';
    error?: string;
}

const MAX_FILE_SIZE_MB = 50;
const ALLOWED_TYPES = [
    'image/jpeg', 'image/png', 'image/gif', 'image/webp',
    'application/pdf',
    'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.ms-powerpoint', 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'text/plain', 'text/csv',
    'application/zip', 'application/x-rar-compressed',
    'video/mp4', 'video/avi', 'video/mov', 'video/wmv',
    'audio/mp3', 'audio/wav', 'audio/m4a'
];

const FileUploadModal: React.FC<FileUploadModalProps> = ({
    isOpen,
    onClose,
    preSelectedProjectId,
    preSelectedMeetingId
}) => {
    const [files, setFiles] = useState<UploadFile[]>([]);
    const [selectedProjectId, setSelectedProjectId] = useState(preSelectedProjectId || '');
    const [selectedMeetingId, setSelectedMeetingId] = useState(preSelectedMeetingId || '');
    const [isDragOver, setIsDragOver] = useState(false);
    const [hasShownProjectWarning, setHasShownProjectWarning] = useState(false);
    const [hasShownMeetingWarning, setHasShownMeetingWarning] = useState(false);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const queryClient = useQueryClient();

    // Fetch projects and meetings for selection
    const { data: projectsData } = useQuery({
        queryKey: queryKeys.projects,
        queryFn: () => getMyProjects({ limit: 50 }),
        enabled: isOpen,
    });

    const { data: meetingsData } = useQuery({
        queryKey: queryKeys.personalMeetings,
        queryFn: () => getPersonalMeetings({ limit: 50 }),
        enabled: isOpen,
    });

    const projects = useMemo(() => projectsData?.data || [], [projectsData?.data]);
    const meetings = useMemo(() => meetingsData?.data || [], [meetingsData?.data]);

    // Update selections when props change
    React.useEffect(() => {
        if (preSelectedProjectId) setSelectedProjectId(preSelectedProjectId);
        if (preSelectedMeetingId) setSelectedMeetingId(preSelectedMeetingId);
    }, [preSelectedProjectId, preSelectedMeetingId]);

    // Clean up invalid selected IDs when lists change
    React.useEffect(() => {
        if (selectedProjectId && projects.length > 0 && !hasShownProjectWarning) {
            const projectExists = projects.some(project => project.id === selectedProjectId);
            if (!projectExists) {
                setSelectedProjectId('');
                setHasShownProjectWarning(true);
                // Use setTimeout to avoid showing toast during render
                setTimeout(() => {
                    showToast('warning', 'Dự án đã chọn không còn hợp lệ. Vui lòng chọn lại.');
                }, 100);
            }
        }
    }, [projects, selectedProjectId, hasShownProjectWarning]);

    React.useEffect(() => {
        if (selectedMeetingId && meetings.length > 0 && !hasShownMeetingWarning) {
            const meetingExists = meetings.some(meeting => meeting.id === selectedMeetingId);
            if (!meetingExists) {
                setSelectedMeetingId('');
                setHasShownMeetingWarning(true);
                // Use setTimeout to avoid showing toast during render
                setTimeout(() => {
                    showToast('warning', 'Cuộc họp đã chọn không còn hợp lệ. Vui lòng chọn lại.');
                }, 100);
            }
        }
    }, [meetings, selectedMeetingId, hasShownMeetingWarning]);

    // Reset warning flags when selections change
    React.useEffect(() => {
        if (selectedProjectId) {
            setHasShownProjectWarning(false);
        }
    }, [selectedProjectId]);

    React.useEffect(() => {
        if (selectedMeetingId) {
            setHasShownMeetingWarning(false);
        }
    }, [selectedMeetingId]);

    const uploadFileMutation = useMutation({
        mutationFn: async ({ uploadData, fileId }: { uploadData: FileUploadData; fileId: string }) => {
            const result = await uploadFile(uploadData);

            // Update file status to completed
            setFiles(prev => prev.map(f =>
                f.id === fileId
                    ? { ...f, status: 'completed' as const, progress: 100 }
                    : f
            ));

            return result;
        },
        onSuccess: () => {
            // Invalidate related queries
            queryClient.invalidateQueries({ queryKey: queryKeys.files });
            queryClient.invalidateQueries({ queryKey: queryKeys.projects });
            queryClient.invalidateQueries({ queryKey: queryKeys.meetings });
            showToast('success', 'Tất cả tệp tin đã được tải lên thành công!');
        },
        onError: (error, variables) => {
            console.error('Failed to upload file:', error);
            showToast('error', 'Có lỗi xảy ra khi tải lên tệp tin. Vui lòng thử lại.');
            // Update file status to error
            setFiles(prev => prev.map(f =>
                f.id === variables.fileId
                    ? { ...f, status: 'error' as const, error: 'Upload failed' }
                    : f
            ));
        },
    });

    const validateFile = (file: File): string | null => {
        // Check file size
        if (file.size > MAX_FILE_SIZE_MB * 1024 * 1024) {
            return `File quá lớn. Kích thước tối đa là ${MAX_FILE_SIZE_MB}MB`;
        }

        // Check file type
        if (!ALLOWED_TYPES.includes(file.type)) {
            return 'Loại file không được hỗ trợ';
        }

        return null;
    };

    const addFiles = useCallback((fileList: FileList) => {
        const newFiles: UploadFile[] = [];

        for (let i = 0; i < fileList.length; i++) {
            const file = fileList[i];
            const validationError = validateFile(file);

            newFiles.push({
                file,
                id: `${Date.now()}-${i}`,
                progress: 0,
                status: validationError ? 'error' : 'pending',
                error: validationError || undefined,
            });
        }

        setFiles(prev => [...(prev || []), ...newFiles]);
    }, []);

    const removeFile = (fileId: string) => {
        setFiles(prev => prev.filter(f => f.id !== fileId));
    };

    const startUpload = async () => {
        if (files.length === 0) return;

        // Validate selected project and meeting IDs
        if (selectedProjectId) {
            const projectExists = projects.some(project => project.id === selectedProjectId);
            if (!projectExists) {
                showToast('error', 'Dự án đã chọn không hợp lệ. Vui lòng chọn lại.');
                return;
            }
        }

        if (selectedMeetingId) {
            const meetingExists = meetings.some(meeting => meeting.id === selectedMeetingId);
            if (!meetingExists) {
                showToast('error', 'Cuộc họp đã chọn không hợp lệ. Vui lòng chọn lại.');
                return;
            }
        }

        const validFiles = files.filter(f => f.status === 'pending');

        for (const uploadFile of validFiles) {
            // Update status to uploading
            setFiles(prev => prev.map(f =>
                f.id === uploadFile.id
                    ? { ...f, status: 'uploading' as const, progress: 0 }
                    : f
            ));

            const uploadData: FileUploadData = {
                file: uploadFile.file,
                project_id: selectedProjectId || undefined,
                meeting_id: selectedMeetingId || undefined,
            };

            uploadFileMutation.mutate({ uploadData, fileId: uploadFile.id });
        }
    };

    const handleDragOver = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        setIsDragOver(true);
    }, []);

    const handleDragLeave = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        setIsDragOver(false);
    }, []);

    const handleDrop = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        setIsDragOver(false);

        const droppedFiles = e.dataTransfer.files;
        if (droppedFiles.length > 0) {
            addFiles(droppedFiles);
        }
    }, [addFiles]);

    const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
        const selectedFiles = e.target.files;
        if (selectedFiles && selectedFiles.length > 0) {
            addFiles(selectedFiles);
        }
        // Reset input value to allow selecting the same file again
        e.target.value = '';
    };

    const getFileIcon = (file: File): string => {
        const type = file.type;

        if (type.startsWith('image/')) return '🖼️';
        if (type.startsWith('video/')) return '🎥';
        if (type.startsWith('audio/')) return '🎵';
        if (type.includes('pdf')) return '📕';
        if (type.includes('word') || type.includes('document')) return '📝';
        if (type.includes('spreadsheet') || type.includes('excel')) return '📊';
        if (type.includes('presentation') || type.includes('powerpoint')) return '📽️';
        if (type.includes('zip') || type.includes('rar')) return '📦';
        if (type.includes('text')) return '📄';

        return '📄';
    };

    const formatFileSize = (bytes: number): string => {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    };

    const hasValidFiles = files.some(f => f.status === 'pending');
    const isUploading = files.some(f => f.status === 'uploading');
    const completedCount = files.filter(f => f.status === 'completed').length;
    const totalFiles = files.length;

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white dark:bg-gray-800 rounded-lg p-6 w-full max-w-2xl mx-4 max-h-[90vh] overflow-y-auto">
                <div className="flex justify-between items-center mb-4">
                    <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                        Tải lên tệp tin
                    </h2>
                    <button
                        onClick={onClose}
                        className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                    >
                        ✕
                    </button>
                </div>

                {/* Project/Meeting Selection */}
                <div className="mb-4 space-y-3">
                    <div>
                        <label htmlFor="project-select" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                            Chọn dự án (tùy chọn)
                        </label>
                        <select
                            id="project-select"
                            value={selectedProjectId}
                            onChange={(e) => setSelectedProjectId(e.target.value)}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                        >
                            <option value="">Không liên kết với dự án</option>
                            {projects.map((project) => (
                                <option key={project.id} value={project.id}>
                                    {project.name}
                                </option>
                            ))}
                        </select>
                    </div>

                    <div>
                        <label htmlFor="meeting-select" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                            Chọn cuộc họp (tùy chọn)
                        </label>
                        <select
                            id="meeting-select"
                            value={selectedMeetingId}
                            onChange={(e) => setSelectedMeetingId(e.target.value)}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                        >
                            <option value="">Không liên kết với cuộc họp</option>
                            {meetings.map((meeting) => (
                                <option key={meeting.id} value={meeting.id}>
                                    {meeting.title || 'Chưa có tiêu đề'}
                                </option>
                            ))}
                        </select>
                    </div>
                </div>

                {/* File Drop Area */}
                <div
                    onDragOver={handleDragOver}
                    onDragLeave={handleDragLeave}
                    onDrop={handleDrop}
                    className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${isDragOver
                        ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                        : 'border-gray-300 dark:border-gray-600'
                        }`}
                >
                    <div className="text-4xl mb-4">📁</div>
                    <p className="text-gray-600 dark:text-gray-400 mb-4">
                        Kéo và thả tệp tin vào đây hoặc{' '}
                        <button
                            onClick={() => fileInputRef.current?.click()}
                            className="text-blue-600 hover:text-blue-700 underline"
                        >
                            chọn tệp tin
                        </button>
                    </p>
                    <p className="text-sm text-gray-500">
                        Hỗ trợ: Hình ảnh, PDF, Word, Excel, PowerPoint, Video, Audio, ZIP
                    </p>
                    <p className="text-sm text-gray-500">
                        Kích thước tối đa: {MAX_FILE_SIZE_MB}MB mỗi tệp
                    </p>

                    <input
                        ref={fileInputRef}
                        type="file"
                        multiple
                        onChange={handleFileSelect}
                        className="hidden"
                        accept={ALLOWED_TYPES.join(',')}
                    />
                </div>

                {/* File List */}
                {files.length > 0 && (
                    <div className="mt-6">
                        <h3 className="text-lg font-medium mb-3">
                            Tệp tin đã chọn ({files.length})
                        </h3>
                        <div className="space-y-3 max-h-60 overflow-y-auto">
                            {files.map((uploadFile) => (
                                <div
                                    key={uploadFile.id}
                                    className={`flex items-center justify-between p-3 border rounded-md ${uploadFile.status === 'error'
                                        ? 'border-red-300 bg-red-50 dark:bg-red-900/20'
                                        : uploadFile.status === 'completed'
                                            ? 'border-green-300 bg-green-50 dark:bg-green-900/20'
                                            : 'border-gray-300 dark:border-gray-600'
                                        }`}
                                >
                                    <div className="flex items-center space-x-3 flex-1 min-w-0">
                                        <span className="text-lg">{getFileIcon(uploadFile.file)}</span>
                                        <div className="flex-1 min-w-0">
                                            <p className="text-sm font-medium truncate">
                                                {uploadFile.file.name}
                                            </p>
                                            <p className="text-xs text-gray-500">
                                                {formatFileSize(uploadFile.file.size)}
                                            </p>
                                            {uploadFile.error && (
                                                <p className="text-xs text-red-600">{uploadFile.error}</p>
                                            )}
                                        </div>
                                    </div>

                                    <div className="flex items-center space-x-2">
                                        {uploadFile.status === 'uploading' && (
                                            <div className="flex items-center space-x-2">
                                                <div className="w-16 bg-gray-200 rounded-full h-2">
                                                    <div
                                                        className="bg-blue-600 h-2 rounded-full transition-all"
                                                        style={{ width: `${uploadFile.progress}%` }}
                                                    ></div>
                                                </div>
                                                <span className="text-xs text-gray-500">
                                                    {uploadFile.progress}%
                                                </span>
                                            </div>
                                        )}

                                        {uploadFile.status === 'completed' && (
                                            <span className="text-green-600 text-sm">✓ Hoàn thành</span>
                                        )}

                                        {uploadFile.status === 'error' && (
                                            <span className="text-red-600 text-sm">✗ Lỗi</span>
                                        )}

                                        <button
                                            onClick={() => removeFile(uploadFile.id)}
                                            disabled={uploadFile.status === 'uploading'}
                                            className="text-gray-400 hover:text-gray-600 disabled:opacity-50"
                                        >
                                            ✕
                                        </button>
                                    </div>
                                </div>
                            ))}
                        </div>

                        {/* Upload Progress Summary */}
                        {completedCount > 0 && (
                            <div className="mt-3 text-sm text-gray-600 dark:text-gray-400">
                                Đã tải lên: {completedCount}/{totalFiles} tệp tin
                            </div>
                        )}
                    </div>
                )}

                {/* Action Buttons */}
                <div className="flex justify-end space-x-3 mt-6">
                    <button
                        onClick={onClose}
                        className="px-4 py-2 text-gray-600 hover:text-gray-800 dark:text-gray-400 dark:hover:text-gray-200"
                        disabled={isUploading}
                    >
                        Đóng
                    </button>

                    {hasValidFiles && (
                        <button
                            onClick={startUpload}
                            disabled={isUploading}
                            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center"
                        >
                            {isUploading ? (
                                <>
                                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                                    Đang tải lên...
                                </>
                            ) : (
                                `Tải lên ${files.filter(f => f.status === 'pending').length} tệp tin`
                            )}
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
};

export default FileUploadModal;
