"use client";

import React, { createContext, useContext, useState, useEffect, ReactNode, useCallback } from "react";
import { useVoice } from "@/contexts/VoiceContext";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: number;
}

interface NexusContextType {
  // Voice State
  isListening: boolean;
  setIsListening: React.Dispatch<React.SetStateAction<boolean>>;
  toggleListening: () => Promise<void>;
  isMuted: boolean;
  setIsMuted: React.Dispatch<React.SetStateAction<boolean>>;
  toggleMute: () => Promise<void>;
  isSpeaking: boolean;
  volume: number;
  setVolume: React.Dispatch<React.SetStateAction<number>>;
  activeCall: any | null; // Kept for UI compatibility
  setActiveCall: any;
  isChecking: boolean;
  setIsChecking: React.Dispatch<React.SetStateAction<boolean>>;
  voiceState: string;
  systemMetrics: any; // Real-time backend metrics via WebSocket
  workspaceState: any;
  pendingPermission: { sessionId: string; command: string } | null;
  authorizeAdminPermission: (approved: boolean) => void;
  activeAgentTier: {
    tier: string;
    provider: string;
    model: string;
    themePrimary: string;
    themeAccent: string;
  } | null;
  
  // Chat State
  messages: Message[];
  setMessages: React.Dispatch<React.SetStateAction<Message[]>>;
  addMessage: (msg: Omit<Message, "id" | "timestamp">) => void;
  sendMessage: (args: { content: string; model?: string }) => Promise<void>;
  isSending: boolean;
  setIsSending: React.Dispatch<React.SetStateAction<boolean>>;
  
  // UI State
  uiMode: "voice" | "chat";
  setUiMode: (mode: "voice" | "chat") => void;
  selectedModel: string;
  setSelectedModel: (model: string) => void;
  persona: string;
  setPersona: (persona: string) => void;
  perplexityMode: boolean;
  setPerplexityMode: (mode: boolean) => void;
  ttsProvider: string;
  setTtsProvider: (provider: string) => void;
  language: string;
  setLanguage: (lang: string) => void;
  voiceEngine: string;
  setVoiceEngine: (engine: string) => void;
  // WS-confirmed active engine (use this for real-time decisions, not voiceEngine)
  activeEngine: string;
  voice: string;
  setVoice: (voice: string) => void;
  speed: number;
  setSpeed: (speed: number) => void;
  pitch: number;
  setPitch: (pitch: number) => void;
  voiceVolume: number;
  setVoiceVolume: (volume: number) => void;
  testVoice: (text?: string) => void;
}

const NexusContext = createContext<NexusContextType | undefined>(undefined);

export function NexusProvider({ children }: { children: ReactNode }) {
  const [isListening, setIsListening] = useState(false);
  const [activeCall, setActiveCall] = useState<any | null>(null);
  const [isMuted, setIsMuted] = useState(false);
  const [volume, setVolume] = useState(0);
  const [isChecking, setIsChecking] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isSending, setIsSending] = useState(false);
  const [uiMode, setUiMode] = useState<"voice" | "chat">("voice");
  const [selectedModel, _setSelectedModel] = useState("gemini-2.5-flash-native-audio-dialog");

  // Load initial preferences on mount
  useEffect(() => {
    const savedModel = localStorage.getItem("nexus_llm_model");
    if (savedModel) _setSelectedModel(savedModel);
  }, []);

  const setSelectedModel = (model: string) => {
    _setSelectedModel(model);
    localStorage.setItem("nexus_llm_model", model);
  };
  const [persona, setPersona] = useState<string>("nexus_male");
  const [perplexityMode, setPerplexityMode] = useState(true);
  const [ttsProvider, setTtsProvider] = useState("gemini");
  const [language, setLanguage] = useState("auto");
  const [voiceEngine, setVoiceEngineState] = useState("standard");
  const [voiceState, setVoiceState] = useState<string>("idle");
  const [voice, setVoice] = useState("");
  const [speed, setSpeed] = useState(1.0);
  const [pitch, setPitch] = useState(0);
  const [voiceVolume, setVoiceVolume] = useState(100);

  useEffect(() => {
    if (typeof window !== 'undefined') {
        const savedEngine = localStorage.getItem('nexus_voice_engine');
        if (savedEngine) setVoiceEngineState(savedEngine);
        
        const savedProvider = localStorage.getItem('nexus_tts_provider');
        if (savedProvider) setTtsProvider(savedProvider);
        
        const savedVoice = localStorage.getItem('nexus_voice');
        if (savedVoice) setVoice(savedVoice);
        
        const savedSpeed = localStorage.getItem('nexus_speed');
        if (savedSpeed) setSpeed(parseFloat(savedSpeed));
        
        const savedPitch = localStorage.getItem('nexus_pitch');
        if (savedPitch) setPitch(parseInt(savedPitch, 10));
        
        const savedVolume = localStorage.getItem('nexus_volume');
        if (savedVolume) setVoiceVolume(parseInt(savedVolume, 10));

        // Load Session History with automatic retries for hot-reloads
        const sessionId = localStorage.getItem('nexus_session_id');
        if (sessionId) {
            const fetchHistory = async (retries = 5, delay = 1000) => {
                for (let i = 0; i < retries; i++) {
                    try {
                        const res = await fetch(`http://localhost:8001/api/history/${sessionId}`);
                        if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
                        const data = await res.json();
                        if (data.history && data.history.length > 0) {
                            const loadedMessages = data.history.map((msg: any, idx: number) => ({
                                id: `hist_${idx}`,
                                role: msg.role,
                                content: msg.content,
                                timestamp: msg.timestamp ? new Date(msg.timestamp).getTime() : Date.now()
                            }));
                            setMessages(loadedMessages);
                        }
                        return; // Success, exit loop
                    } catch (err) {
                        if (i === retries - 1) {
                            console.error("Failed to load history after retries:", err);
                        } else {
                            // Wait before retrying (gives the backend time to finish booting)
                            await new Promise(resolve => setTimeout(resolve, delay));
                        }
                    }
                }
            };
            fetchHistory();
        }
    }
  }, []);

  // Wrap setters to persist
  const setTtsProviderPersist = useCallback((val: string) => {
    setTtsProvider(val);
    if (typeof window !== 'undefined') localStorage.setItem('nexus_tts_provider', val);
  }, []);
  
  const setVoicePersist = useCallback((val: string) => {
    setVoice(val);
    if (typeof window !== 'undefined') localStorage.setItem('nexus_voice', val);
  }, []);
  
  const setSpeedPersist = useCallback((val: number) => {
    setSpeed(val);
    if (typeof window !== 'undefined') localStorage.setItem('nexus_speed', val.toString());
  }, []);
  
  const setPitchPersist = useCallback((val: number) => {
    setPitch(val);
    if (typeof window !== 'undefined') localStorage.setItem('nexus_pitch', val.toString());
  }, []);
  
  const setVoiceVolumePersist = useCallback((val: number) => {
    setVoiceVolume(val);
    if (typeof window !== 'undefined') localStorage.setItem('nexus_volume', val.toString());
  }, []);

  const setVoiceEngine = useCallback((engine: string) => {
    setVoiceEngineState(engine);
    if (typeof window !== 'undefined') {
        localStorage.setItem('nexus_voice_engine', engine);
    }
    // We would ideally reload or reconnect the voice context here
    window.location.reload();
  }, []);

  const addMessage = useCallback((msg: Omit<Message, "id" | "timestamp">) => {
    setMessages(prev => [
      ...prev,
      {
        ...msg,
        id: Math.random().toString(36).substring(7),
        timestamp: Date.now()
      }
    ]);
  }, []);

  const handleTranscript = useCallback((text: string) => {
    addMessage({ role: "user", content: text });
  }, [addMessage]);

  const handleAgentMessage = useCallback((text: string, _isParagraphEnd: boolean) => {
    setMessages(prev => {
      const lastMsg = prev[prev.length - 1];
      if (lastMsg && lastMsg.role === "assistant") {
        // If text is empty or duplicate of the full message, ignore
        if (!text || lastMsg.content === text) return prev;
        
        const newMessages = [...prev];
        // Only append if it's not a complete overwrite (agent_message sends the full text)
        if (text.length > lastMsg.content.length && text.startsWith(lastMsg.content)) {
            newMessages[newMessages.length - 1] = { ...lastMsg, content: text };
        } else if (lastMsg.content.length > 0 && text !== lastMsg.content) {
            newMessages[newMessages.length - 1] = { 
                ...lastMsg, 
                content: lastMsg.content + (lastMsg.content.endsWith(" ") ? "" : " ") + text.trim() 
            };
        }
        return newMessages;
      } else {
        // Start new assistant message
        if (!text) return prev;
        const initialMsg: Message = {
          id: Math.random().toString(36).substring(7),
          role: "assistant",
          content: text.trim(),
          timestamp: Date.now()
        };
        return [...prev, initialMsg];
      }
    });
  }, []);



  const {
    isListening: voiceIsListening,
    micCaptured,
    isSpeaking,
    activeEngine,
    systemMetrics,
    workspaceState,
    pendingPermission,
    activeAgentTier,
    authorizeAdminPermission,
    startListening,
    stopListening,
    setMicMuted,
    sendTextMessage,
    setCallbacks,
    updateSettings,
    testVoice
  } = useVoice();

  React.useEffect(() => {
    updateSettings({
      persona,
      ttsProvider,
      language,
      voiceEngine,
      voice,
      speed,
      pitch,
      volume: voiceVolume,
      model: selectedModel
    });
  }, [persona, ttsProvider, language, voiceEngine, voice, speed, pitch, voiceVolume, selectedModel, updateSettings]);

  React.useEffect(() => {
    setCallbacks({
      onTranscript: handleTranscript,
      onAgentMessage: handleAgentMessage,
    });
  }, [setCallbacks, handleTranscript, handleAgentMessage]);

  // Sync state
  React.useEffect(() => {
    if (isSpeaking) {
      setVoiceState("speaking");
    } else if (voiceIsListening) {
      setVoiceState("listening");
    } else {
      setVoiceState("idle");
    }
  }, [isSpeaking, voiceIsListening]);


  // Sync hook state with context state
  React.useEffect(() => {
    setIsListening(voiceIsListening);
  }, [voiceIsListening]);

  const sendMessage = useCallback(async ({ content }: { content: string }): Promise<void> => {
    if (!content.trim() || isSending) return;
    setIsSending(true);
    addMessage({ role: "user", content });
    
    // Send text directly to the Python Nexus Voice Backend WebSocket
    sendTextMessage(content);
    setIsSending(false);
    
    // Filter out empty streaming artifacts left by AI turn chunks
    setMessages(prev => prev.filter(m => m.content.trim() !== "" || m.role === "user"));
  }, [addMessage, isSending, sendTextMessage]);

  const toggleMute = useCallback(async () => {
    setIsMuted(!isMuted);
  }, [isMuted]);

  const toggleListening = useCallback(async () => {
    if (isListening) {
      stopListening(); // This sets mic as muted
    } else {
      setIsChecking(true);
      if (!micCaptured) {
         await startListening();
      } else {
         setMicMuted(false);
      }
      setIsChecking(false);
    }
  }, [isListening, micCaptured, startListening, stopListening, setMicMuted]);

  return (
    <NexusContext.Provider value={{
      isListening, setIsListening, toggleListening,
      isMuted, setIsMuted, toggleMute,
      isSpeaking,
      volume, setVolume,
      activeCall, setActiveCall,
      isChecking, setIsChecking,
      messages, setMessages, addMessage,
      sendMessage, isSending, setIsSending,
      uiMode, setUiMode,
      selectedModel, setSelectedModel,
      persona, setPersona,
      perplexityMode,
      setPerplexityMode,
      ttsProvider,
      setTtsProvider: setTtsProviderPersist,
      language,
      setLanguage,
      voiceEngine,
      setVoiceEngine,
      activeEngine,
      voice,
      setVoice: setVoicePersist,
      speed,
      setSpeed: setSpeedPersist,
      pitch,
      setPitch: setPitchPersist,
      voiceVolume,
      setVoiceVolume: setVoiceVolumePersist,
      testVoice,
      systemMetrics,
      workspaceState,
      voiceState,
      pendingPermission,
      authorizeAdminPermission,
      activeAgentTier,
    }}>
      {children}
    </NexusContext.Provider>
  );
}

export function useNexus() {
  const context = useContext(NexusContext);
  if (context === undefined) {
    throw new Error("useNexus must be used within a NexusProvider");
  }
  return context;
}
