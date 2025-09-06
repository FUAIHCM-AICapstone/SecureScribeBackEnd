import { QueryClient } from '@tanstack/react-query';

const queryClient = new QueryClient({
    defaultOptions: {
        queries: {
            retry: 2,
            refetchOnWindowFocus: false,
            staleTime: 5 * 60 * 1000, // 5 minutes
            gcTime: 10 * 60 * 1000, // 10 minutes (formerly cacheTime)
            refetchOnMount: false, // Prevent refetch on mount if data is still fresh
            refetchOnReconnect: 'always',
        },
        mutations: {
            retry: 1,
        },
    },
});

export default queryClient;
