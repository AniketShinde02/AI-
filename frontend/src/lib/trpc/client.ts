import { createTRPCReact } from '@trpc/react-query';
import type { AppRouter } from './router';

/**
 * tRPC React Hooks
 * Use these in client components for type-safe data fetching.
 */
export const trpc = createTRPCReact<AppRouter>();
