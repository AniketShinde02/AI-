import { trpc } from '@/lib/trpc/client';
import { useNexus } from '@/contexts/NexusContext';

/**
 * useNexusChat Hook
 * Handles text-based chat interactions.
 * Uses global NexusContext for message persistence and synchronization.
 */
export const useNexusChat = () => {
  const { messages, addMessage, isSending, setIsSending, selectedModel } = useNexus();

  const chatMutation = trpc.chat.useMutation({
    onMutate: async ({ content }) => {
      setIsSending(true);
      addMessage({
        role: 'user',
        content: content,
      });
    },
    onError: (err) => {
      console.error('Nexus Chat Error:', err);
      setIsSending(false);
      addMessage({
        role: 'assistant',
        content: 'I encountered an error while processing your request. Please try again.',
      });
    },
    onSuccess: (data) => {
      setIsSending(false);
      addMessage({
        role: data.role as 'assistant',
        content: data.content,
      });
    },
    onSettled: () => {
      setIsSending(false);
    },
  });

  const sendMessage = ({ content, model }: { content: string; model: string }) => {
    const userId = typeof window !== 'undefined' ? sessionStorage.getItem('nexus_user_id') : 'anonymous';
    chatMutation.mutate({ 
      content, 
      userId: userId || 'anonymous', 
      model: model || selectedModel 
    });
  };

  return {
    sendMessage,
    isSending,
    messages,
  };
};
