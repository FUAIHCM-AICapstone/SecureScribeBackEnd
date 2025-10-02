import { QueryClient } from '@tanstack/react-query';

const queryClient = new QueryClient({
    defaultOptions: {
        queries: {
            retry: 2,
            refetchOnWindowFocus: false,
            staleTime: 2 * 60 * 1000, // 2 minutes for dashboard data
            gcTime: 10 * 60 * 1000, // 10 minutes
            refetchOnMount: 'always', // Always refetch dashboard data on mount
            refetchOnReconnect: 'always',
        },
        mutations: {
            retry: 1,
            onError: (error) => {
                console.error('Mutation error:', error);
            },
        },
    },
});

// Query Keys for consistent caching
export const queryKeys = {
    projects: ['projects'] as const,
    project: (id: string) => ['projects', id] as const,
    projectMeetings: (id: string) => ['projects', id, 'meetings'] as const,
    projectFiles: (id: string) => ['projects', id, 'files'] as const,
    tasksByProject: (id: string) => ['projects', id, 'tasks'] as const,

    meetings: ['meetings'] as const,
    personalMeetings: ['meetings', 'personal'] as const,
    meeting: (id: string) => ['meetings', id] as const,
    meetingFiles: (id: string) => ['meetings', id, 'files'] as const,
    tasksByMeeting: (id: string) => ['meetings', id, 'tasks'] as const,

    files: ['files'] as const,
    file: (id: string) => ['files', id] as const,

    user: ['user'] as const,
    userStats: ['user', 'stats'] as const,

    tasks: ['tasks'] as const,
    task: (id: string) => ['tasks', id] as const,

    googleCalendar: ['google-calendar'] as const,
    googleCalendarStatus: ['google-calendar', 'status'] as const,
};

export default queryClient;
