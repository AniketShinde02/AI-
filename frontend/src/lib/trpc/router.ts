import { z } from 'zod';
import { router, publicProcedure } from './trpc';
import { StreamClient } from '@stream-io/node-sdk';

/**
 * tRPC Router Definition
 * Centralizes all API procedures with full type safety and documentation.
 */
export const appRouter = router({
  /**
   * Retrieves search suggestions based on partial input.
   * Useful for autocomplete in the main search bar.
   */
  getSuggestions: publicProcedure
    .meta({ description: 'Fetch search suggestions' })
    .input(z.object({ q: z.string().min(2) }))
    .query(async ({ input }) => {
      const suggestions = [
        `How to use ${input.q}?`,
        `Latest news about ${input.q}`,
        `${input.q} best practices`,
        `Compare ${input.q} with competitors`
      ];
      return suggestions;
    }),

  /**
   * Main Text Chat mutation.
   * Interfaces with Groq API for real-time text-based AI assistance.
   */
  chat: publicProcedure
    .meta({ description: 'Execute a text-based AI chat completion' })
    .input(z.object({
      content: z.string(),
      userId: z.string().optional(),
      model: z.string().optional()
    }))
    .mutation(async ({ input }) => {
      const groqApiKey = process.env.GROQ_API_KEY;
      const model = input.model || process.env.LLM_MODEL || 'llama-3.3-70b-versatile';

      if (!groqApiKey) {
        throw new Error('Groq API not configured');
      }

      const res = await fetch('https://api.groq.com/openai/v1/chat/completions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${groqApiKey}`,
        },
        body: JSON.stringify({
          messages: [
            { role: 'system', content: 'You are Nexus, a helpful AI assistant. Be concise and helpful.' },
            { role: 'user', content: input.content }
          ],
          model,
          temperature: 0.7,
          max_tokens: 1024,
        }),
      });

      const data = await res.json();
      const aiReply = data?.choices?.[0]?.message?.content ?? 'Sorry, I could not process that.';

      return {
        id: `nexus_${Date.now()}`,
        role: 'assistant',
        content: aiReply,
        timestamp: Date.now(),
      };
    }),

  /**
   * Voice Session Initialization.
   * Generates a WebRTC token and signals the Python Backend to join as a voice participant.
   */
  getVoiceSession: publicProcedure
    .meta({ description: 'Initialize a real-time voice call session' })
    .input(z.object({
      userId: z.string(),
      agentType: z.string().default('general'),
      model: z.string().optional(),
      persona: z.string().default('female')
    }))
    .mutation(async ({ input }) => {
      const apiKey = process.env.NEXT_PUBLIC_STREAM_API_KEY;
      const apiSecret = process.env.STREAM_API_SECRET;

      if (!apiKey || !apiSecret) {
        throw new Error('Stream configuration missing');
      }

      const serverClient = new StreamClient(apiKey, apiSecret, { timeout: 30000 });
      const sessionId = `nexus_session_${input.userId.split('_').pop()}`;
      const callType = 'default';
      const agentId = 'nexus-agent-1';

      await serverClient.upsertUsers([
        { id: input.userId, role: 'admin', name: 'User' },
        { id: agentId, role: 'admin', name: `Nexus ${input.agentType} Agent` }
      ]);

      const call = serverClient.video.call(callType, sessionId);
      await call.getOrCreate({
        data: {
          created_by_id: input.userId,
          members: [
            { user_id: input.userId, role: 'admin' },
            { user_id: agentId, role: 'admin' }
          ],
        },
      });

      const token = serverClient.createToken(input.userId);
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://127.0.0.1:8001';

      try {
        const response = await fetch(`${backendUrl}/voice/session`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            userId: input.userId,
            agentType: input.agentType,
            callId: sessionId,
            persona: input.persona
          }),
        });
        
        if (!response.ok) {
          const text = await response.text();
          console.error(`[tRPC] Python Backend returned ${response.status}: ${text}`);
        }
      } catch (e) {
        console.error(`[tRPC] Could not reach Python Backend at ${backendUrl}/voice/session`);
        console.error(e);
      }

      return {
        apiKey,
        token,
        userId: input.userId,
        agentId,
        callId: sessionId,
        callType
      };
    })
});

// Export type definition of API
export type AppRouter = typeof appRouter;
