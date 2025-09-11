'use client';

import React, { useState, useRef, useEffect, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
    searchDocuments,
    ragChat,
    searchCorpus,
    getConversationHistory,
    clearConversationHistory,
    validateSearchQuery
} from '../../services/api';
import { getMyProjects } from '../../services/api/project';
import { getPersonalMeetings } from '../../services/api/meeting';
import { queryKeys } from '../../lib/queryClient';
import { showToast } from '../../hooks/useShowToast';
import type {
    SearchResult,
    SearchRequest,
    RAGChatRequest,
    CorpusSearchRequest,
    ConversationHistory,
    CorpusResult
} from '../../types/search.type';

type TabType = 'search' | 'chat' | 'corpus';

const SearchComponent: React.FC = () => {
    // Basic search states
    const [searchQuery, setSearchQuery] = useState('');
    const [selectedProjectId, setSelectedProjectId] = useState('');
    const [selectedMeetingId, setSelectedMeetingId] = useState('');
    const [isSearching, setIsSearching] = useState(false);
    const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
    const [hasSearched, setHasSearched] = useState(false);

    // RAG Chat states
    const [chatQuery, setChatQuery] = useState('');
    const [chatResponse, setChatResponse] = useState('');
    const [sessionId, setSessionId] = useState('');
    const [conversationHistory, setConversationHistory] = useState<ConversationHistory | null>(null);
    const [isChatting, setIsChatting] = useState(false);

    // Corpus search states
    const [corpusQuery, setCorpusQuery] = useState('');
    const [corpusResults, setCorpusResults] = useState<CorpusResult[]>([]);
    const [isCorpusSearching, setIsCorpusSearching] = useState(false);

    // UI states
    const [activeTab, setActiveTab] = useState<TabType>('search');

    // Refs for auto-scroll
    const chatResponseRef = useRef<HTMLDivElement>(null);
    const corpusResultsRef = useRef<HTMLDivElement>(null);

    // Fetch projects and meetings for filters
    const { data: projectsData } = useQuery({
        queryKey: queryKeys.projects,
        queryFn: () => getMyProjects({ limit: 50 }),
    });

    const { data: meetingsData } = useQuery({
        queryKey: queryKeys.personalMeetings,
        queryFn: () => getPersonalMeetings({ limit: 50 }),
    });

    const projects = projectsData?.data || [];
    const meetings = meetingsData?.data || [];

    // Load conversation history when session changes
    const loadConversationHistory = useCallback(async () => {
        if (!sessionId) return;
        try {
            const response = await getConversationHistory(sessionId);
            if (response.success && response.data) {
                setConversationHistory(response.data);
            }
        } catch (error) {
            console.error('Failed to load conversation history:', error);
            setConversationHistory(null);
        }
    }, [sessionId]);

    useEffect(() => {
        if (sessionId) {
            loadConversationHistory();
        }
    }, [sessionId, loadConversationHistory]);

    // Auto-scroll to bottom when new content is added
    useEffect(() => {
        if (chatResponseRef.current) {
            chatResponseRef.current.scrollTop = chatResponseRef.current.scrollHeight;
        }
    }, [chatResponse]);

    useEffect(() => {
        if (corpusResultsRef.current) {
            corpusResultsRef.current.scrollTop = corpusResultsRef.current.scrollHeight;
        }
    }, [corpusResults]);

    const handleSearch = async (e: React.FormEvent) => {
        e.preventDefault();

        // Validate query
        const validation = validateSearchQuery(searchQuery);
        if (!validation.valid) {
            showToast('warning', validation.message || 'Query không hợp lệ');
            return;
        }

        setIsSearching(true);
        setHasSearched(true);

        try {
            console.log('🔍 Performing search with query:', searchQuery);

            const searchParams: SearchRequest = {
                query: searchQuery.trim(),
                limit: 20,
            };

            if (selectedProjectId) {
                searchParams.project_id = selectedProjectId;
            }

            if (selectedMeetingId) {
                searchParams.meeting_id = selectedMeetingId;
            }

            const response = await searchDocuments(searchParams);

            if (response.success && response.data) {
                setSearchResults(response.data.results);
                console.log(`✅ Found ${response.data.results.length} search results`);

                if (response.data.results.length === 0) {
                    showToast('info', 'Không tìm thấy kết quả nào phù hợp với từ khóa của bạn');
                } else {
                    showToast('success', `Tìm thấy ${response.data.results.length} kết quả`);
                }
            } else {
                console.error('❌ Search failed:', response.message);
                showToast('error', response.message || 'Có lỗi xảy ra khi tìm kiếm');
                setSearchResults([]);
            }
        } catch (error) {
            console.error('❌ Search error:', error);
            showToast('error', 'Có lỗi xảy ra khi tìm kiếm. Vui lòng thử lại.');
            setSearchResults([]);
        } finally {
            setIsSearching(false);
        }
    };

    const handleRAGChat = async () => {
        if (!chatQuery.trim()) {
            showToast('warning', 'Vui lòng nhập câu hỏi');
            return;
        }

        setIsChatting(true);
        const currentQuery = chatQuery;
        setChatQuery(''); // Clear input immediately

        try {
            const params: RAGChatRequest = {
                query: currentQuery.trim(),
                top_k: 5,
                session_id: sessionId || undefined
            };

            const response = await ragChat(params);
            if (response.success && response.data) {
                setChatResponse(response.data.response);
                setSessionId(response.data.session_id || '');
                await loadConversationHistory(); // Refresh conversation history
            } else {
                showToast('error', response.message || 'Có lỗi khi chat với AI');
            }
        } catch (error) {
            console.error('❌ Chat error:', error);
            showToast('error', 'Có lỗi xảy ra khi chat với AI. Vui lòng thử lại.');
        } finally {
            setIsChatting(false);
        }
    };

    const handleCorpusSearch = async () => {
        if (!corpusQuery.trim()) {
            showToast('warning', 'Vui lòng nhập từ khóa tìm kiếm corpus');
            return;
        }

        setIsCorpusSearching(true);

        try {
            const params: CorpusSearchRequest = {
                query: corpusQuery.trim(),
                collection_name: 'vietnam_history',
                top_k: 10
            };

            const response = await searchCorpus(params);
            if (response.success && response.data) {
                setCorpusResults(response.data.results);
                showToast('success', `Tìm thấy ${response.data.results.length} kết quả trong corpus`);
            } else {
                showToast('error', response.message || 'Có lỗi khi tìm kiếm corpus');
                setCorpusResults([]);
            }
        } catch (error) {
            console.error('❌ Corpus search error:', error);
            showToast('error', 'Có lỗi xảy ra khi tìm kiếm corpus. Vui lòng thử lại.');
            setCorpusResults([]);
        } finally {
            setIsCorpusSearching(false);
        }
    };

    const clearSearch = () => {
        setSearchQuery('');
        setSelectedProjectId('');
        setSelectedMeetingId('');
        setSearchResults([]);
        setHasSearched(false);
    };

    const clearChat = async () => {
        if (sessionId) {
            try {
                await clearConversationHistory(sessionId);
                setConversationHistory(null);
                setChatResponse('');
                showToast('success', 'Đã xóa lịch sử cuộc trò chuyện');
            } catch (error) {
                console.error('❌ Clear chat error:', error);
                showToast('error', 'Có lỗi khi xóa lịch sử cuộc trò chuyện');
            }
        }
        setChatQuery('');
    };

    const clearCorpusSearch = () => {
        setCorpusQuery('');
        setCorpusResults([]);
    };

    const formatFileSize = (bytes: number): string => {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    };

    const getFileIcon = (mimeType?: string): string => {
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

    const highlightText = (text: string, query: string): React.ReactNode => {
        if (!query.trim()) return text;

        const regex = new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
        const parts = text.split(regex);

        return parts.map((part, index) =>
            regex.test(part) ? (
                <mark key={index} className="bg-yellow-200 dark:bg-yellow-800 px-1 rounded">
                    {part}
                </mark>
            ) : (
                part
            )
        );
    };

    const tabs = [
        { id: 'search' as TabType, label: '🔍 Tìm kiếm', icon: '🔍' },
        { id: 'chat' as TabType, label: '🤖 Chat AI', icon: '🤖' },
        { id: 'corpus' as TabType, label: '📚 Corpus', icon: '📚' },
    ];

    return (
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-6">
            {/* Header */}
            <div className="mb-6">
                <h2 className="text-2xl font-semibold text-gray-900 dark:text-white mb-2">
                    🔍 Hệ thống Tìm kiếm & AI
                </h2>
                <p className="text-gray-600 dark:text-gray-400">
                    Tìm kiếm ngữ nghĩa, chat với AI, và khám phá corpus tri thức
                </p>
            </div>

            {/* Tab Navigation */}
            <div className="flex space-x-1 mb-6 bg-gray-100 dark:bg-gray-700 p-1 rounded-lg">
                {tabs.map((tab) => (
                    <button
                        key={tab.id}
                        onClick={() => setActiveTab(tab.id)}
                        className={`flex-1 px-4 py-2 text-sm font-medium rounded-md transition-colors ${activeTab === tab.id
                                ? 'bg-white dark:bg-gray-600 text-gray-900 dark:text-white shadow-sm'
                                : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
                            }`}
                    >
                        {tab.icon} {tab.label.split(' ').slice(1).join(' ')}
                    </button>
                ))}
            </div>

            {/* Search Tab */}
            {activeTab === 'search' && (
                <>
                    {/* Search Form */}
                    <form onSubmit={handleSearch} className="space-y-4">
                        <div className="flex gap-4">
                            <div className="flex-1">
                                <input
                                    type="text"
                                    value={searchQuery}
                                    onChange={(e) => setSearchQuery(e.target.value)}
                                    placeholder="Nhập từ khóa tìm kiếm... (ví dụ: machine learning, project management)"
                                    className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                                    disabled={isSearching}
                                />
                            </div>
                            <button
                                type="submit"
                                disabled={isSearching || !searchQuery.trim()}
                                className="px-6 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white rounded-lg font-medium transition-colors flex items-center gap-2"
                            >
                                {isSearching ? (
                                    <>
                                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                                        Đang tìm...
                                    </>
                                ) : (
                                    <>
                                        🔍 Tìm kiếm
                                    </>
                                )}
                            </button>
                            {(hasSearched || searchQuery || selectedProjectId || selectedMeetingId) && (
                                <button
                                    type="button"
                                    onClick={clearSearch}
                                    className="px-4 py-3 bg-gray-500 hover:bg-gray-600 text-white rounded-lg font-medium transition-colors"
                                >
                                    🗑️ Xóa
                                </button>
                            )}
                        </div>

                        {/* Filters */}
                        <div className="flex gap-4 flex-wrap">
                            <div className="min-w-[200px]">
                                <select
                                    value={selectedProjectId}
                                    onChange={(e) => setSelectedProjectId(e.target.value)}
                                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                                >
                                    <option value="">Tất cả dự án</option>
                                    {projects.map((project) => (
                                        <option key={project.id} value={project.id}>
                                            {project.name}
                                        </option>
                                    ))}
                                </select>
                            </div>

                            <div className="min-w-[200px]">
                                <select
                                    value={selectedMeetingId}
                                    onChange={(e) => setSelectedMeetingId(e.target.value)}
                                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                                >
                                    <option value="">Tất cả cuộc họp</option>
                                    {meetings.map((meeting) => (
                                        <option key={meeting.id} value={meeting.id}>
                                            {meeting.title || 'Chưa có tiêu đề'}
                                        </option>
                                    ))}
                                </select>
                            </div>
                        </div>
                    </form>

                    {/* Search Results */}
                    {hasSearched && (
                        <div className="mt-6">
                            <div className="flex items-center justify-between mb-4">
                                <h3 className="text-lg font-medium text-gray-900 dark:text-white">
                                    Kết quả tìm kiếm
                                </h3>
                                {searchResults.length > 0 && (
                                    <span className="text-sm text-gray-600 dark:text-gray-400">
                                        {searchResults.length} kết quả
                                    </span>
                                )}
                            </div>

                            {isSearching ? (
                                <div className="flex items-center justify-center py-12">
                                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                                    <span className="ml-3 text-gray-600 dark:text-gray-400">Đang tìm kiếm...</span>
                                </div>
                            ) : searchResults.length > 0 ? (
                                <div className="space-y-4">
                                    {searchResults.map((result) => (
                                        <div
                                            key={`${result.file_id}-${result.chunk_index}`}
                                            className="border border-gray-200 dark:border-gray-600 rounded-lg p-4 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                                        >
                                            <div className="flex items-start justify-between mb-2">
                                                <div className="flex items-center space-x-3 flex-1">
                                                    <span className="text-2xl">{getFileIcon(result.mime_type)}</span>
                                                    <div className="flex-1">
                                                        <h4 className="font-medium text-gray-900 dark:text-white truncate">
                                                            {result.filename || `File ${result.file_id.slice(-8)}`}
                                                        </h4>
                                                        <div className="flex items-center space-x-4 text-sm text-gray-600 dark:text-gray-400">
                                                            <span>Độ tương tự: {(result.score * 100).toFixed(1)}%</span>
                                                            <span>Kích thước: {formatFileSize(result.chunk_size)}</span>
                                                            {result.mime_type && <span>Loại: {result.mime_type}</span>}
                                                        </div>
                                                    </div>
                                                </div>
                                            </div>

                                            <div className="mt-3">
                                                <p className="text-gray-700 dark:text-gray-300 leading-relaxed">
                                                    {highlightText(result.text, searchQuery)}
                                                </p>
                                            </div>

                                            <div className="mt-3 flex items-center justify-between">
                                                <span className="text-xs text-gray-500 dark:text-gray-400">
                                                    Chunk {result.chunk_index + 1}
                                                </span>
                                                <button
                                                    onClick={() => {
                                                        // You can implement navigation to file here
                                                        console.log('Navigate to file:', result.file_id);
                                                        showToast('info', 'Tính năng xem chi tiết file sẽ được thêm sau');
                                                    }}
                                                    className="text-xs bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded"
                                                >
                                                    Xem file
                                                </button>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            ) : hasSearched && !isSearching ? (
                                <div className="text-center py-12">
                                    <div className="text-4xl mb-4">🔍</div>
                                    <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                                        Không tìm thấy kết quả
                                    </h3>
                                    <p className="text-gray-600 dark:text-gray-400">
                                        Thử tìm kiếm với từ khóa khác hoặc kiểm tra chính tả
                                    </p>
                                </div>
                            ) : null}
                        </div>
                    )}
                </>
            )}

            {/* Chat Tab */}
            {activeTab === 'chat' && (
                <div className="space-y-4">
                    {/* Chat Interface */}
                    <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4 min-h-[400px] flex flex-col">
                        {/* Chat Messages */}
                        <div
                            ref={chatResponseRef}
                            className="flex-1 overflow-y-auto mb-4 max-h-[300px] space-y-3"
                        >
                            {conversationHistory?.turns.map((turn, index) => (
                                <div key={index} className="space-y-2">
                                    <div className="flex items-start space-x-2">
                                        <span className="text-blue-600 font-medium">Bạn:</span>
                                        <p className="text-gray-800 dark:text-gray-200 bg-blue-50 dark:bg-blue-900/20 rounded-lg px-3 py-2 flex-1">
                                            {turn.user}
                                        </p>
                                    </div>
                                    <div className="flex items-start space-x-2">
                                        <span className="text-green-600 font-medium">AI:</span>
                                        <p className="text-gray-800 dark:text-gray-200 bg-green-50 dark:bg-green-900/20 rounded-lg px-3 py-2 flex-1">
                                            {turn.ai}
                                        </p>
                                    </div>
                                </div>
                            ))}

                            {chatResponse && !conversationHistory?.turns.some(t => t.ai === chatResponse) && (
                                <div className="flex items-start space-x-2">
                                    <span className="text-green-600 font-medium">AI:</span>
                                    <p className="text-gray-800 dark:text-gray-200 bg-green-50 dark:bg-green-900/20 rounded-lg px-3 py-2 flex-1">
                                        {chatResponse}
                                    </p>
                                </div>
                            )}

                            {!conversationHistory?.turns.length && !chatResponse && (
                                <div className="text-center text-gray-500 dark:text-gray-400 py-8">
                                    <div className="text-4xl mb-4">🤖</div>
                                    <p>Bắt đầu cuộc trò chuyện với AI bằng cách đặt câu hỏi!</p>
                                </div>
                            )}
                        </div>

                        {/* Chat Input */}
                        <div className="flex gap-2">
                            <input
                                type="text"
                                value={chatQuery}
                                onChange={(e) => setChatQuery(e.target.value)}
                                onKeyPress={(e) => e.key === 'Enter' && !isChatting && handleRAGChat()}
                                placeholder="Hỏi AI bất kỳ câu hỏi nào về tài liệu của bạn..."
                                className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-600 text-gray-900 dark:text-white"
                                disabled={isChatting}
                            />
                            <button
                                onClick={handleRAGChat}
                                disabled={isChatting || !chatQuery.trim()}
                                className="px-4 py-2 bg-green-600 hover:bg-green-700 disabled:bg-gray-400 text-white rounded-lg font-medium transition-colors flex items-center gap-2"
                            >
                                {isChatting ? (
                                    <>
                                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                                        Đang suy nghĩ...
                                    </>
                                ) : (
                                    <>💬 Gửi</>
                                )}
                            </button>
                            <button
                                onClick={clearChat}
                                className="px-4 py-2 bg-gray-500 hover:bg-gray-600 text-white rounded-lg font-medium transition-colors"
                            >
                                🗑️ Xóa
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Corpus Tab */}
            {activeTab === 'corpus' && (
                <div className="space-y-4">
                    {/* Corpus Search Form */}
                    <div className="flex gap-4">
                        <div className="flex-1">
                            <input
                                type="text"
                                value={corpusQuery}
                                onChange={(e) => setCorpusQuery(e.target.value)}
                                onKeyPress={(e) => e.key === 'Enter' && !isCorpusSearching && handleCorpusSearch()}
                                placeholder="Tìm kiếm trong corpus tri thức... (ví dụ: lịch sử Đảng Cộng sản Việt Nam)"
                                className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                                disabled={isCorpusSearching}
                            />
                        </div>
                        <button
                            onClick={handleCorpusSearch}
                            disabled={isCorpusSearching || !corpusQuery.trim()}
                            className="px-6 py-3 bg-purple-600 hover:bg-purple-700 disabled:bg-gray-400 text-white rounded-lg font-medium transition-colors flex items-center gap-2"
                        >
                            {isCorpusSearching ? (
                                <>
                                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                                    Đang tìm...
                                </>
                            ) : (
                                <>📚 Tìm kiếm</>
                            )}
                        </button>
                        {corpusQuery && (
                            <button
                                onClick={clearCorpusSearch}
                                className="px-4 py-3 bg-gray-500 hover:bg-gray-600 text-white rounded-lg font-medium transition-colors"
                            >
                                🗑️ Xóa
                            </button>
                        )}
                    </div>

                    {/* Corpus Results */}
                    <div
                        ref={corpusResultsRef}
                        className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4 min-h-[300px] overflow-y-auto"
                    >
                        {corpusResults.length > 0 ? (
                            <div className="space-y-4">
                                {corpusResults.map((result) => (
                                    <div
                                        key={result.rank}
                                        className="border border-gray-200 dark:border-gray-600 rounded-lg p-4 bg-white dark:bg-gray-800"
                                    >
                                        <div className="flex items-center justify-between mb-2">
                                            <span className="text-sm font-medium text-purple-600 dark:text-purple-400">
                                                Rank #{result.rank} • Độ tương tự: {(result.score * 100).toFixed(1)}%
                                            </span>
                                            <span className="text-xs text-gray-500 dark:text-gray-400">
                                                {result.source_file} • Chunk {result.chunk_index}
                                            </span>
                                        </div>

                                        {result.section && (
                                            <h4 className="font-medium text-gray-900 dark:text-white mb-2">
                                                📑 {result.section}
                                            </h4>
                                        )}

                                        <p className="text-gray-700 dark:text-gray-300 leading-relaxed">
                                            {highlightText(result.text, corpusQuery)}
                                        </p>

                                        <div className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                                            {result.word_count} từ • {result.document_type}
                                            {result.topic && ` • ${result.topic}`}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        ) : corpusQuery && !isCorpusSearching ? (
                            <div className="text-center py-12">
                                <div className="text-4xl mb-4">📚</div>
                                <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                                    Không tìm thấy kết quả trong corpus
                                </h3>
                                <p className="text-gray-600 dark:text-gray-400">
                                    Thử tìm kiếm với từ khóa khác hoặc kiểm tra chính tả
                                </p>
                            </div>
                        ) : (
                            <div className="text-center py-12">
                                <div className="text-4xl mb-4">📚</div>
                                <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                                    Corpus Tri thức
                                </h3>
                                <p className="text-gray-600 dark:text-gray-400">
                                    Tìm kiếm trong bộ sưu tập tài liệu lịch sử và chính trị Việt Nam
                                </p>
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* Search Tips */}
            {!hasSearched && activeTab === 'search' && (
                <div className="mt-6 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
                    <h4 className="font-medium text-blue-900 dark:text-blue-100 mb-2">
                        💡 Mẹo tìm kiếm
                    </h4>
                    <ul className="text-sm text-blue-800 dark:text-blue-200 space-y-1">
                        <li>• Sử dụng câu hỏi tự nhiên: "how does machine learning work?"</li>
                        <li>• Tìm kiếm bằng nhiều từ khóa: "project management best practices"</li>
                        <li>• Lọc theo dự án hoặc cuộc họp để thu hẹp kết quả</li>
                        <li>• Hệ thống hỗ trợ tìm kiếm ngữ nghĩa, không chỉ khớp chính xác</li>
                    </ul>
                </div>
            )}
        </div>
    );
};

export default SearchComponent;
