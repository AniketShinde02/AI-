import { fetchRequestHandler } from '@trpc/server/adapters/fetch';
import { appRouter } from '@/lib/trpc/router';

/**
 * Next.js 15 App Router tRPC Handler
 */
const handler = (req: Request) =>
  fetchRequestHandler({
    endpoint: '/api/trpc',
    req,
    router: appRouter,
    createContext: () => ({}), // Add context here if needed (auth, db, etc)
  });

export { handler as GET, handler as POST };
