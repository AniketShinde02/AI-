"use client";

import React, { createContext, useContext, useState, ReactNode, useCallback, useEffect } from "react";
import { useGeminiLive } from "@/hooks/useGeminiLive";

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
  systemMetrics: null; // Not available in Gemini Live mode
  
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
        const newMessages = [...prev];
        const updatedMsg = { ...lastMsg, content: lastMsg.content + text };
        newMessages[newMessages.length - 1] = updatedMsg;
        
        // If it was a paragraph end, we'll start a new empty assistant message for the next chunk
        if (isParagraphEnd) {
          return [
            ...newMessages,
            {
              id: Math.random().toString(36).substring(7),
              role: "assistant",
              content: "",
              timestamp: Date.now()
            }
          ];
        }
        return newMessages;
      } else {
        // Start new assistant message
        const initialMsg: Message = {
          id: Math.random().toString(36).substring(7),
          role: "assistant",
          content: text,
          timestamp: Date.now()
        };
        
        if (isParagraphEnd) {
          return [
            ...prev,
            initialMsg,
            {
              id: Math.random().toString(36).substring(7),
              role: "assistant",
              content: "",
              timestamp: Date.now()
            }
          ];
        }
        return [...prev, initialMsg];
      }
    });
  }, []);

  const handleToolCall = useCallback(async (toolCall: any) => {
    // Map tool name to UI state
    let stateName = "RUNNING TOOL";
    if (toolCall.name === "search_web") stateName = "SEARCHING WEB";
    else if (toolCall.name === "consultOracle" || toolCall.name === "run_rag") stateName = "CONSULTING ORACLE";
    else if (toolCall.name === "run_command") stateName = "EXECUTING COMMAND";
    else if (toolCall.name === "update_preferences") stateName = "UPDATING MEMORY";
    else if (toolCall.name === "get_user_memory") stateName = "RETRIEVING MEMORY";
    else if (toolCall.name === "delete_user_preference") stateName = "DELETING MEMORY";
    
    setVoiceState(stateName);
    try {
      // Hardcoded fetch to FastAPI execute-tool for now
      const res = await fetch("http://localhost:8000/execute-tool", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ functionCalls: [toolCall] })
      });
      const data = await res.json();
      setVoiceState("thinking");
      return data;
    } catch (e) {
      console.error(e);
      setVoiceState("idle");
      return { error: "Tool execution failed" };
    }
  }, []);

  const {
    isListening: voiceIsListening,
    micCaptured,
    isSpeaking,
    connect,
    disconnect,
    startListening,
    stopListening,
    setMicMuted,
    sendTextMessage,
    setApiKey
  } = useGeminiLive({
    onTranscript: handleTranscript,
    onAgentMessage: handleAgentMessage,
    onToolCall: handleToolCall
  });

  // Inject the Gemini API key once on mount
  useEffect(() => {
    const key = process.env.NEXT_PUBLIC_GEMINI_API_KEY || "";
    if (key) setApiKey(key);
  }, [setApiKey]);

  const systemMetrics = null; // Not available in Gemini Live mode

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

  // Connect once the API key has been injected (key is set synchronously in the effect above)
  React.useEffect(() => {
    connect();
    return () => disconnect();
  }, [connect, disconnect]);

  // Sync hook state with context state
  React.useEffect(() => {
    setIsListening(voiceIsListening);
  }, [voiceIsListening]);

  const sendMessage = useCallback(async ({ content }: { content: string }): Promise<void> => {
    if (!content.trim() || isSending) return;
    setIsSending(true);
    addMessage({ role: "user", content });
    
    // Send text directly to Gemini Live WebSocket
    sendTextMessage(content);
    setIsSending(false);
    
    // Filter out empty streaming artifacts left by Gemini Live turn chunks
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
