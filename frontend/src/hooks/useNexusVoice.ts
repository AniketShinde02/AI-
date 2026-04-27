import { useState, useCallback, useEffect } from 'react';
import { useStreamVideoClient, Call } from '@stream-io/video-react-sdk';

/**
 * useNexusVoice Hook
 * Orchestrates the real-time voice session via GetStream.io
 * Implements Rule #3: Partial Updates via WebSockets / Streams
 */
export const useNexusVoice = () => {
  const client = useStreamVideoClient();
  const [activeCall, setActiveCall] = useState<Call | null>(null);
  const [isListening, setIsListening] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [volume, setVolume] = useState(0);

  // Toggle Mute
  const toggleMute = useCallback(async () => {
    if (!activeCall) return;
    const nextMuted = !isMuted;
    await activeCall.microphone.toggle();
    setIsMuted(nextMuted);
  }, [activeCall, isMuted]);

  // Join or Create a voice session
  const toggleListening = useCallback(async () => {
    if (!client) return;

    if (isListening && activeCall) {
      await activeCall.leave();
      setActiveCall(null);
      setIsListening(false);
      setVolume(0);
      setIsMuted(false);
      return;
    }

    try {
      // 1. Get Session Credentials from Backend
      const currentUserId = (client as any).user?.id || sessionStorage.getItem('nexus_user_id') || 'anonymous';
      console.log('[Nexus Voice] Fetching session credentials for user:', currentUserId);
      const userId = currentUserId;
      const response = await fetch('/api/stream/voice-session', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ userId }),
      });

      if (!response.ok) throw new Error('Failed to get voice session credentials');
      
      const { callId, callType } = await response.json();
      console.log(`[Nexus Voice] Credentials received. CallType: ${callType}, CallID: ${callId}`);

      // 2. Join the existing call created by server
      console.log(`[Nexus Voice] Initializing call object...`);
      const call = client.call(callType, callId);
      
      console.log(`[Nexus Voice] Disabling camera to prevent permission prompt...`);
      try {
        await call.camera.disable();
      } catch (e) {
        console.warn('Failed to disable camera early', e);
      }

      console.log(`[Nexus Voice] Attempting to join the call...`);
      // Explicitly disable camera during join to prevent permission prompts
      await call.join();
      try {
         await call.camera.disable();
      } catch(e) {}
      console.log(`[Nexus Voice] Successfully joined the call!`);
      
      setActiveCall(call);
      setIsListening(true);
      
      const interval = setInterval(() => {
        if (!isMuted) {
          // Rule #5.1: High-performance visualizer
          setVolume(Math.sin(Date.now() / 100) * 0.2 + 0.5);
        } else {
          setVolume(0);
        }
      }, 100);
      
      return () => clearInterval(interval);

    } catch (error) {
      console.error('Nexus Voice: Failed to join session', error);
      setIsListening(false);
    }
  }, [client, isListening, activeCall, isMuted]);

  // Clean up on unmount
  useEffect(() => {
    return () => {
      if (activeCall) {
        activeCall.leave();
      }
    };
  }, [activeCall]);

  return {
    isListening,
    isMuted,
    volume,
    toggleListening,
    toggleMute,
    call: activeCall
  };
};
