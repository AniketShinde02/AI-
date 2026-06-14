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
  setCallbacks: (callbacks: {
    onTranscript?: (text: string) => void;
    onAgentMessage?: (text: string, isFinal: boolean) => void;
  }) => void;
}

const VoiceContext = createContext<VoiceContextType | undefined>(undefined);

// ─── MODULE-LEVEL SINGLETON GUARD ───────────────────────────────────────────
// This survives React StrictMode's double-invoke (mount → unmount → remount).
// A ref inside the component does NOT survive StrictMode remount because the
// entire component instance is torn down. This variable lives in module scope
// and is set exactly once per browser tab lifetime.
let _globalConnectCalled = false;
// ────────────────────────────────────────────────────────────────────────────

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

  // Connect exactly once per browser session — module guard prevents StrictMode double-fire.
  // No cleanup return: this provider lives at app root and should NEVER disconnect on remount.
  React.useEffect(() => {
    if (_globalConnectCalled) {
      console.info("[VoiceProvider] ♻️  Session reused — skipping duplicate connect");
      return;
    }
    _globalConnectCalled = true;
    console.info("[VoiceProvider] 🔌 Initiating first WebSocket connection");
    voiceState.connect();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Empty deps — run once, no cleanup, intentional

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
