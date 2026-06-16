"use client";

import React, { createContext, useContext, ReactNode } from "react";
import { useNexusVoice } from "@/hooks/useNexusVoice";

interface VoiceContextType {
  isConnected: boolean;
  isListening: boolean;
  isSpeaking: boolean;
  micCaptured: boolean;
  systemMetrics: any;
  connect: () => void;
  disconnect: () => void;
  startListening: () => Promise<void>;
  stopListening: () => void;
  setMicMuted: (muted: boolean) => void;
  sendTextMessage: (text: string, speech?: boolean) => void;
  updateSettings: (settings: any) => void;
  testVoice: (text?: string) => void;
  setCallbacks: (callbacks: {
    onTranscript?: (text: string) => void;
    onAgentMessage?: (text: string, isFinal: boolean) => void;
  }) => void;
}

const VoiceContext = createContext<VoiceContextType | undefined>(undefined);

// Global connect guard removed to allow proper React lifecycle.

export function VoiceProvider({ children }: { children: ReactNode }) {
  // Use a ref to store callbacks so we can update them without re-rendering the hook
  const callbacksRef = React.useRef<{
    onTranscript?: (text: string) => void;
    onAgentMessage?: (text: string, isFinal: boolean) => void;
  }>({});

  const voiceState = useNexusVoice({
    onTranscript: (text: string) => callbacksRef.current.onTranscript?.(text),
    onAgentMessage: (text: string, isFinal: boolean) =>
      callbacksRef.current.onAgentMessage?.(text, isFinal),
  });

  const setCallbacks = React.useCallback(
    (callbacks: {
      onTranscript?: (text: string) => void;
      onAgentMessage?: (text: string, isFinal: boolean) => void;
    }) => {
      callbacksRef.current = callbacks;
    },
    []
  );

  React.useEffect(() => {
    console.info("[VoiceProvider] 🔌 Initiating WebSocket connection");
    voiceState.connect();
    
    return () => {
      console.info("[VoiceProvider] 🧹 Cleaning up WebSocket connection");
      voiceState.disconnect();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <VoiceContext.Provider value={{ ...voiceState, setCallbacks }}>
      {children}
    </VoiceContext.Provider>
  );
}

export function useVoice() {
  const context = useContext(VoiceContext);
  if (context === undefined) {
    throw new Error("useVoice must be used within a VoiceProvider");
  }
  return context;
}
