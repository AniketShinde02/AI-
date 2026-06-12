import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';

/**
 * Global Health Monitoring Hook
 * Implements Rule #8: Global Monitoring & Health
 * Regularly polls the backend to ensure connectivity and system health.
 */
export const useHealthCheck = () => {
  return useQuery({
    queryKey: ['system-health'],
    queryFn: async () => {
      const controller = new AbortController();
      const id = setTimeout(() => controller.abort(), 3000);
      try {
        const response = await apiClient.get('/api/health', {
          signal: controller.signal,
        });
        clearTimeout(id);
        return response;
      } catch (error) {
        clearTimeout(id);
        console.error('System Health Check Failed:', error);
        throw error;
      }
    },
    // Poll every 30 seconds
    refetchInterval: 30000,
    // Don't show global loading state for background health checks
    placeholderData: (prev) => prev,
    retry: 3,
  });
};
