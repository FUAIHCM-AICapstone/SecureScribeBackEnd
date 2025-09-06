'use client';

import React, { useState, useEffect, useRef } from 'react';
import {
    getFiles,
    uploadFile,
    deleteFile,
    bulkFileOperation
} from '../../services/api/file';
import type { FileResponse, FileUploadData } from '../../types/file.type';
import Button from '../ui/Button';
import { Skeleton } from '../ui/Skeleton';

const FileManager: React.FC = () => {
    const [files, setFiles] = useState<FileResponse[]>([]);
    const [loading, setLoading] = useState(true);
    const [uploading, setUploading] = useState(false);
    const [selectedFiles, setSelectedFiles] = useState<string[]>([]);
    const [showUploadModal, setShowUploadModal] = useState(false);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const [uploadData, setUploadData] = useState<FileUploadData>({
        file: new File([], ''),
    });

    useEffect(() => {
        loadFiles();
    }, []);

    const loadFiles = async () => {
        try {
            setLoading(true);
            const response = await getFiles({ limit: 50 });
            setFiles(response.data);
        } catch (error) {
            console.error('Failed to load files:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0];
        if (file) {
            setUploadData({ file });
        }
    };

    const handleUpload = async () => {
        if (!uploadData.file || uploadData.file.size === 0) return;

        try {
            setUploading(true);
            await uploadFile(uploadData);
            setShowUploadModal(false);
            setUploadData({ file: new File([], '') });
            loadFiles();
            if (fileInputRef.current) {
                fileInputRef.current.value = '';
            }
        } catch (error) {
            console.error('Failed to upload file:', error);
        } finally {
            setUploading(false);
        }
    };

    const handleDeleteFile = async (fileId: string) => {
        if (!confirm('Bạn có chắc chắn muốn xóa tệp tin này?')) return;

        try {
            await deleteFile(fileId);
            loadFiles();
        } catch (error) {
            console.error('Failed to delete file:', error);
        }
    };

    const handleBulkDelete = async () => {
        if (selectedFiles.length === 0) return;
        if (!confirm(`Bạn có chắc chắn muốn xóa ${selectedFiles.length} tệp tin đã chọn?`)) return;

        try {
            await bulkFileOperation({
                file_ids: selectedFiles,
                operation: 'delete',
            });
            setSelectedFiles([]);
            loadFiles();
        } catch (error) {
            console.error('Failed to delete files:', error);
        }
    };

    const toggleFileSelection = (fileId: string) => {
        setSelectedFiles(prev =>
            prev.includes(fileId)
                ? prev.filter(id => id !== fileId)
                : [...prev, fileId]
        );
    };

    const selectAllFiles = () => {
        if (selectedFiles.length === files.length) {
            setSelectedFiles([]);
        } else {
            setSelectedFiles(files.map(file => file.id));
        }
    };

    const formatFileSize = (bytes: number | null | undefined): string => {
        if (!bytes) return '0 B';
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(1024));
        return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
    };

    const getFileIcon = (mimeType: string | null | undefined): string => {
        if (!mimeType) return '📄';

        if (mimeType.startsWith('image/')) return '🖼️';
        if (mimeType.startsWith('video/')) return '🎥';
        if (mimeType.startsWith('audio/')) return '🎵';
        if (mimeType.includes('pdf')) return '📕';
        if (mimeType.includes('word') || mimeType.includes('document')) return '📝';
        if (mimeType.includes('spreadsheet') || mimeType.includes('excel')) return '📊';
        if (mimeType.includes('presentation') || mimeType.includes('powerpoint')) return '📽️';
        if (mimeType.includes('zip') || mimeType.includes('rar')) return '📦';

        return '📄';
    };

    if (loading) {
        return (
            <div className="p-6">
                <div className="flex justify-between items-center mb-6">
                    <h2 className="text-2xl font-bold">Quản lý tệp tin</h2>
                    <Skeleton width={120} height={40} />
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {Array.from({ length: 9 }).map((_, i) => (
                        <div key={i} className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
                            <div className="flex items-center space-x-3 mb-3">
                                <Skeleton width={32} height={32} variant="circular" />
                                <div className="flex-1">
                                    <Skeleton height={16} className="mb-1" />
                                    <Skeleton height={12} width="60%" />
                                </div>
                            </div>
                            <Skeleton height={12} width="40%" />
                        </div>
                    ))}
                </div>
            </div>
        );
    }

    return (
        <div className="p-6">
            <div className="flex justify-between items-center mb-6">
                <div className="flex items-center space-x-4">
                    <h2 className="text-2xl font-bold">Quản lý tệp tin</h2>
                    {selectedFiles.length > 0 && (
                        <span className="text-sm text-gray-600 dark:text-gray-400">
                            Đã chọn {selectedFiles.length} tệp tin
                        </span>
                    )}
                </div>
                <div className="flex space-x-2">
                    {selectedFiles.length > 0 && (
                        <Button
                            onClick={handleBulkDelete}
                            className="bg-red-600 hover:bg-red-700 text-white"
                        >
                            Xóa ({selectedFiles.length})
                        </Button>
                    )}
                    <Button
                        onClick={() => setShowUploadModal(true)}
                        className="bg-blue-600 hover:bg-blue-700 text-white"
                    >
                        + Tải lên
                    </Button>
                </div>
            </div>

            {files.length === 0 ? (
                <div className="text-center py-12">
                    <div className="text-6xl mb-4">📄</div>
                    <h3 className="text-xl font-semibold mb-2">Chưa có tệp tin nào</h3>
                    <p className="text-gray-600 dark:text-gray-400 mb-6">
                        Tải lên tệp tin đầu tiên của bạn
                    </p>
                    <Button
                        onClick={() => setShowUploadModal(true)}
                        className="bg-blue-600 hover:bg-blue-700 text-white"
                    >
                        Tải lên tệp tin
                    </Button>
                </div>
            ) : (
                <>
                    <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center space-x-4">
                            <label className="flex items-center">
                                <input
                                    type="checkbox"
                                    checked={selectedFiles.length === files.length && files.length > 0}
                                    onChange={selectAllFiles}
                                    className="mr-2"
                                />
                                <span className="text-sm font-medium">Chọn tất cả</span>
                            </label>
                            <span className="text-sm text-gray-600 dark:text-gray-400">
                                {files.length} tệp tin
                            </span>
                        </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {files.map((file) => (
                            <div key={file.id} className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4 hover:shadow-md transition-shadow">
                                <div className="flex items-start justify-between mb-3">
                                    <div className="flex items-center space-x-3 flex-1">
                                        <input
                                            type="checkbox"
                                            checked={selectedFiles.includes(file.id)}
                                            onChange={() => toggleFileSelection(file.id)}
                                            className="mt-1"
                                        />
                                        <div className="text-2xl">
                                            {getFileIcon(file.mime_type)}
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <h4 className="font-medium truncate">
                                                {file.filename || 'Tệp không tên'}
                                            </h4>
                                            <p className="text-sm text-gray-600 dark:text-gray-400 truncate">
                                                {file.mime_type || 'Unknown type'}
                                            </p>
                                        </div>
                                    </div>
                                </div>

                                <div className="text-sm text-gray-500 space-y-1">
                                    <div className="flex justify-between">
                                        <span>Kích thước:</span>
                                        <span>{formatFileSize(file.size_bytes)}</span>
                                    </div>
                                    <div className="flex justify-between">
                                        <span>Ngày tải lên:</span>
                                        <span>{new Date(file.created_at).toLocaleDateString('vi-VN')}</span>
                                    </div>
                                </div>

                                <div className="flex space-x-2 mt-4">
                                    <Button
                                        onClick={() => handleDeleteFile(file.id)}
                                        className="flex-1 bg-red-600 hover:bg-red-700 text-white text-sm"
                                    >
                                        Xóa
                                    </Button>
                                    {file.storage_url && (
                                        <Button
                                            onClick={() => window.open(file.storage_url!, '_blank')}
                                            className="flex-1 bg-green-600 hover:bg-green-700 text-white text-sm"
                                        >
                                            Tải xuống
                                        </Button>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                </>
            )}

            {/* Upload Modal */}
            {showUploadModal && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                    <div className="bg-white dark:bg-gray-800 rounded-lg p-6 w-full max-w-md">
                        <h3 className="text-xl font-semibold mb-4">Tải lên tệp tin</h3>

                        <div className="space-y-4">
                            <div>
                                <label htmlFor="file-upload" className="block text-sm font-medium mb-2">Chọn tệp tin</label>
                                <input
                                    id="file-upload"
                                    ref={fileInputRef}
                                    type="file"
                                    onChange={handleFileSelect}
                                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700"
                                    accept="*/*"
                                />
                                {uploadData.file && uploadData.file.size > 0 && (
                                    <div className="mt-2 text-sm text-gray-600 dark:text-gray-400">
                                        Đã chọn: {uploadData.file.name} ({formatFileSize(uploadData.file.size)})
                                    </div>
                                )}
                            </div>
                        </div>

                        <div className="flex space-x-3 mt-6">
                            <Button
                                onClick={() => {
                                    setShowUploadModal(false);
                                    setUploadData({ file: new File([], '') });
                                    if (fileInputRef.current) {
                                        fileInputRef.current.value = '';
                                    }
                                }}
                                className="flex-1 bg-gray-600 hover:bg-gray-700 text-white"
                                disabled={uploading}
                            >
                                Hủy
                            </Button>
                            <Button
                                onClick={handleUpload}
                                className="flex-1 bg-blue-600 hover:bg-blue-700 text-white"
                                disabled={uploading || !uploadData.file || uploadData.file.size === 0}
                            >
                                {uploading ? 'Đang tải lên...' : 'Tải lên'}
                            </Button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default FileManager;
