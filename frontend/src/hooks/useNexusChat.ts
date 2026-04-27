import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: number;
  status: 'sending' | 'sent' | 'error';
}

/**
 * Nexus Chat Hook
 * Implements Rule #5: Local First & Optimistic Updates
 */
export const useNexusChat = () => {
  const queryClient = useQueryClient();

  const sendMessageMutation = useMutation({
    mutationFn: async (content: string) => {
      const userId = typeof window !== 'undefined' ? sessionStorage.getItem('nexus_user_id') : 'anonymous';
      return apiClient.post('/api/chat', { content, userId });
    },
    // Optimistic Update logic
    onMutate: async (newContent) => {
      // Cancel any outgoing refetches (so they don't overwrite our optimistic update)
      await queryClient.cancelQueries({ queryKey: ['messages'] });

      // Snapshot the previous value
      const previousMessages = queryClient.getQueryData<Message[]>(['messages']) || [];

      // Optimistically add the new message
      const newMessage: Message = {
        id: `msg_${Date.now()}`, // Rule #8: floor-based safe ID
        role: 'user',
        content: newContent,
        timestamp: Date.now(),
        status: 'sending',
      };

      queryClient.setQueryData(['messages'], [...previousMessages, newMessage]);

      // Return a context object with the snapshotted value
      return { previousMessages };
    },
    // If the mutation fails, use the context returned from onMutate to roll back
    onError: (err, newContent, context) => {
      if (context?.previousMessages) {
        queryClient.setQueryData(['messages'], context.previousMessages);
      }
    },
    // Always refetch after error or success:
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['messages'] });
    },
  });

  return {
    sendMessage: sendMessageMutation.mutate,
    isSending: sendMessageMutation.isPending,
    messages: queryClient.getQueryData<Message[]>(['messages']) || [],
  };
};
