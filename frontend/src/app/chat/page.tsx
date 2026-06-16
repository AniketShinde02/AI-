"use client";

import { useNexus } from "@/contexts/NexusContext";
import { MessageList } from "@/components/MessageList";
import { InputArea } from "@/components/InputArea";
import { MessageSquare, Mic, MicOff, Volume2, VolumeX, Zap } from "lucide-react";

export default function ChatPage() {
  const {
    messages,
    isListening,
    isMuted,
    voiceState,
    toggleListening,
    toggleMute,
    uiMode,
    setUiMode,
    isChecking,
    systemMetrics,
  } = useNexus();

  const stateColor =
    voiceState === "listening"
      ? "#00FFFF"
      : voiceState === "speaking"
      ? "#6137FF"
      : voiceState === "idle"
      ? "#10b981"
      : "#f59e0b";

  return (
    <div className="h-full flex flex-col overflow-hidden p-4 gap-4">
      {/* Header */}
      <div className="flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-[#6137FF]/20 border border-[#6137FF]/40 flex items-center justify-center clip-cut">
            <MessageSquare size={16} className="text-[#6137FF]" />
          </div>
          <div>
            <h1 className="text-[11px] font-quantico font-bold uppercase tracking-[0.3em] text-white">Neural Chat</h1>
            <p className="text-[9px] font-mono text-zinc-500 uppercase tracking-widest">Persistent Dialogue Interface</p>
          </div>
        </div>

        {/* Voice Controls */}
        <div className="flex items-center gap-2">
          <div
            className="px-3 py-1 text-[9px] font-bold uppercase tracking-widest border clip-cut-sm"
            style={{ color: stateColor, borderColor: `${stateColor}40`, background: `${stateColor}10` }}
          >
            <span
              className="inline-block w-1.5 h-1.5 rounded-full mr-2 animate-pulse"
              style={{ background: stateColor, boxShadow: `0 0 6px ${stateColor}` }}
            />
            {voiceState.toUpperCase()}
          </div>
          <button
            onClick={toggleMute}
            className={`w-8 h-8 flex items-center justify-center border clip-cut-sm transition-all ${
              isMuted
                ? "bg-[#ff3366]/10 border-[#ff3366]/40 text-[#ff3366]"
                : "bg-white/5 border-white/10 text-zinc-400 hover:text-white"
            }`}
            title={isMuted ? "Unmute" : "Mute"}
          >
            {isMuted ? <VolumeX size={14} /> : <Volume2 size={14} />}
          </button>
          <button
            onClick={toggleListening}
            disabled={isChecking}
            className={`w-8 h-8 flex items-center justify-center border clip-cut-sm transition-all ${
              isListening
                ? "bg-[#ff3366] border-[#ff3366] text-white shadow-[0_0_15px_rgba(255,51,102,0.4)]"
                : "bg-[#6137FF]/20 border-[#6137FF]/40 text-[#6137FF] hover:bg-[#6137FF]/30"
            }`}
            title={isListening ? "Stop Mic" : "Start Mic"}
          >
            {isListening ? <Mic size={14} className="animate-pulse" /> : <MicOff size={14} />}
          </button>
          <button
            onClick={() => setUiMode(uiMode === "chat" ? "voice" : "chat")}
            className={`px-3 py-1 text-[9px] font-bold uppercase tracking-widest border clip-cut-sm transition-all ${
              uiMode === "chat"
                ? "bg-[#00FFFF]/10 border-[#00FFFF]/30 text-[#00FFFF]"
                : "bg-white/5 border-white/10 text-zinc-400 hover:text-white"
            }`}
          >
            <Zap size={12} className="inline mr-1" />
            {uiMode === "chat" ? "Chat Mode" : "Voice Mode"}
          </button>
          
          {/* Latency Metrics */}
          {systemMetrics && (
            <div className="hidden md:flex items-center gap-2 px-3 py-1 bg-black/40 border border-[#00FFFF]/20 clip-cut-sm ml-2">
               <span className="text-[9px] font-mono text-zinc-400">LATENCY:</span>
               <span className="text-[9px] font-bold text-[#00FFFF]">{systemMetrics.total_ms}ms</span>
               <span className="text-[8px] font-mono text-zinc-500">
                 (STT {systemMetrics.stt_ms} | LLM {systemMetrics.llm_ms} | TTS {systemMetrics.tts_ms})
               </span>
            </div>
          )}
        </div>
      </div>

      {/* Messages + Input */}
      <div className="flex-1 flex flex-col min-h-0 bg-[#06060c] border border-[#6137FF]/15 clip-cut overflow-hidden shadow-inner">
        {messages.length === 0 ? (
          <div className="flex-1 flex flex-col items-center justify-center gap-4 opacity-40">
            <MessageSquare size={40} className="text-[#6137FF]" />
            <p className="text-[11px] font-quantico uppercase tracking-widest text-zinc-500">
              Awaiting Command...
            </p>
            <p className="text-[9px] font-mono text-zinc-600">
              Speak or type to initialize dialogue
            </p>
          </div>
        ) : (
          <div className="flex-1 overflow-y-auto scroll-hide p-4">
            <MessageList />
          </div>
        )}

        {/* Input */}
        <div className="shrink-0 border-t border-white/5 p-3 bg-black/40">
          <InputArea />
        </div>
      </div>
    </div>
  );
}
