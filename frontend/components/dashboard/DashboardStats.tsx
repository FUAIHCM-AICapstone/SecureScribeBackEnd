'use client';

import React from 'react';
import type { ProjectStats } from '../../types/project.type';

interface DashboardStatsProps {
    stats: ProjectStats | null;
}

const DashboardStats: React.FC<DashboardStatsProps> = ({ stats }) => {
    if (!stats) {
        return (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
                {Array.from({ length: 4 }).map((_, i) => (
                    <div key={i} className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6">
                        <div className="animate-pulse">
                            <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4 mb-2"></div>
                            <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-1/2"></div>
                        </div>
                    </div>
                ))}
            </div>
        );
    }

    const statCards = [
        {
            label: 'Tổng số dự án',
            value: stats.total_projects,
            icon: '📁',
            color: 'blue',
        },
        {
            label: 'Dự án đang quản lý',
            value: stats.admin_projects,
            icon: '👑',
            color: 'green',
        },
        {
            label: 'Dự án thành viên',
            value: stats.member_projects,
            icon: '👥',
            color: 'purple',
        },
        {
            label: 'Dự án hoạt động',
            value: stats.active_projects,
            icon: '⚡',
            color: 'orange',
        },
    ];

    return (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
            {statCards.map((stat, index) => (
                <div key={index} className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6">
                    <div className="flex items-center justify-between">
                        <div>
                            <p className="text-sm font-medium text-gray-600 dark:text-gray-400">
                                {stat.label}
                            </p>
                            <p className="text-3xl font-bold text-gray-900 dark:text-white">
                                {stat.value}
                            </p>
                        </div>
                        <div className={`text-3xl ${stat.color === 'blue' ? 'text-blue-600' :
                            stat.color === 'green' ? 'text-green-600' :
                                stat.color === 'purple' ? 'text-purple-600' :
                                    'text-orange-600'
                            }`}>
                            {stat.icon}
                        </div>
                    </div>
                </div>
            ))}
        </div>
    );
};

export default DashboardStats;
