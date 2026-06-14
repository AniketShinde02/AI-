"use client";

import React, { createContext, useContext, useState, ReactNode, useCallback } from "react";
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
  persona: "female" | "male";
  setPersona: (persona: "female" | "male") => void;
  perplexityMode: boolean;
  setPerplexityMode: (mode: boolean) => void;
  ttsProvider: string;
  setTtsProvider: (provider: string) => void;
  language: string;
  setLanguage: (lang: string) => void;
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
  const [selectedModel, setSelectedModel] = useState("llama-3.3-70b-versatile");
  const [persona, setPersona] = useState<"female" | "male">("female");
  const [perplexityMode, setPerplexityMode] = useState(true);
  const [ttsProvider, setTtsProvider] = useState("gemini");
  const [language, setLanguage] = useState("auto");
  const [voiceState, setVoiceState] = useState<string>("idle");

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

  const handleAgentMessage = useCallback((text: string, isParagraphEnd: boolean) => {
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
    systemMetrics,
    startListening,
    stopListening,
    setMicMuted,
    sendTextMessage,
    setCallbacks
  } = useVoice();

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
      setTtsProvider,
      language,
      setLanguage,
      systemMetrics,
      voiceState
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
