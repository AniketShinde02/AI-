"use client";

import { ReactNode, useEffect, useState } from 'react';
import { StreamVideo, StreamVideoClient, User } from '@stream-io/video-react-sdk';

/**
 * Nexus Stream Provider
 * Wraps the application to provide GetStream.io context.
 */
export function NexusStreamProvider({ children }: { children: ReactNode }) {
  const [client, setClient] = useState<StreamVideoClient | null>(null);

  useEffect(() => {
    let isMounted = true;

    async function initStream() {
      // Use sessionStorage to keep the user ID stable across reloads (Rule #2 Resilience)
      let userId = typeof window !== 'undefined' ? sessionStorage.getItem('nexus_user_id') : null;
      
      if (!userId) {
        userId = typeof crypto !== 'undefined' && crypto.randomUUID 
          ? `user_${crypto.randomUUID()}`
          : `user_${Math.floor(Date.now() / 1000)}_${Math.floor(Math.random() * 1000)}`;
        if (typeof window !== 'undefined') sessionStorage.setItem('nexus_user_id', userId);
      }
      
      try {
        // Optimized: Reduced frequency by using a stable client setup
        const response = await fetch(`/api/stream/token?userId=${userId}`);
        const data = await response.json();

        if (!isMounted) return;

        if (data.token && data.apiKey && !data.apiKey.includes('your_stream')) {
          const videoClient = new StreamVideoClient({ 
            apiKey: data.apiKey, 
            user: { id: userId, name: 'Nexus User' }, 
            token: data.token,
            options: { logLevel: 'error' }
          });
          setClient(videoClient);
        } else {
          console.warn('Nexus Core: Stream API Key missing or placeholder. Voice features disabled.');
        }
      } catch (error) {
        console.error('Failed to initialize Stream client:', error);
      }
    }

    initStream();

    return () => {
      isMounted = false;
      if (client) {
        client.disconnectUser();
      }
    };
  }, []);

  // FIX: Unconditionally return children to prevent React from completely 
  // destroying and remounting the entire application tree when the client loads.
  // The StreamVideo wrapper is only needed for Video UI components, and should 
  // be placed lower in the tree where those components actually exist.
  if (client) {
    // We initialize the client but do not structurally wrap the whole app,
    // avoiding the 1006 disconnect bug and the initial 5-second freeze.
  }
  return <>{children}</>;
}
