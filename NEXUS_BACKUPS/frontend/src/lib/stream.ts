import { StreamVideoClient, User } from '@stream-io/video-react-sdk';

const apiKey = process.env.NEXT_PUBLIC_STREAM_API_KEY || 'default_key';

/**
 * Nexus Stream Client
 * Manages the connection to GetStream.io for real-time voice streaming.
 * Implements Rule #3: Partial Updates via WebSockets / Streams
 */
export const createStreamClient = (user: User, token: string) => {
  return new StreamVideoClient({ apiKey, user: user as any, token });
};

// Singleton instance for the client (Lazy initialized)
let clientInstance: StreamVideoClient | null = null;

export const getStreamClient = () => {
  if (!clientInstance) {
    throw new Error('Stream client not initialized. Call initStream first.');
  }
  return clientInstance;
};

export const initStream = (user: User, token: string) => {
  if (!clientInstance) {
    clientInstance = createStreamClient(user, token);
  }
  return clientInstance;
};
