"use client";

import { useState } from "react";
import { InputArea } from "@/components/InputArea";
import { useNexus } from "@/contexts/NexusContext";
import { MessageList } from "@/components/MessageList";
import { SystemLogs } from "@/components/SystemLogs";
import { SystemTrace } from "@/components/SystemTrace";
import {
  ScanEye, Mic, MicOff, Cpu, Globe, Command,
  Play, VolumeX, Volume2,
  RefreshCw, ExternalLink, Brain,
  History, MessageSquarePlus,
  Plus, Check, Trash2, StickyNote, CheckSquare, ArrowUp, ArrowDown,
  LayoutDashboard, TerminalSquare, Activity, Database, Settings, ShieldAlert, GitBranch
} from "lucide-react";
import { ThreeOrb, OrbConfig } from "@/components/ThreeOrb";
import { NexusStatus } from "@/components/NexusStatus";
import { SystemTelemetry } from "@/components/SystemTelemetry";
import { logger } from "@/lib/logger";
import { useEffect } from "react";

const getGreeting = () => {
  const hour = new Date().getHours();
  if (hour < 12) return "Good Morning";
  if (hour < 18) return "Good Afternoon";
  return "Good Evening";
};

/* ─── Types ─────────────────────────────────────────── */
interface Task {
  id: string;
  text: string;
  done: boolean;
}
interface Note {
  id: string;
  text: string;
}

/* ─── Tiny helpers ───────────────────────────────────── */
const uid = () => Math.random().toString(36).slice(2, 9);

export default function Home() {
  const { 
    isListening, isMuted, volume, 
    toggleListening, toggleMute, 
    isSending, isChecking,
    voiceState, uiMode, setUiMode
  } = useNexus();
  const [activeTab, setActiveTab] = useState<'chat' | 'trace' | 'tasks' | 'memory'>('chat');

  useEffect(() => {
    logger.info("Nexus System Initialized", { version: "1.0.0", mode: "Autonomous" });
    logger.ai("Neural Link Established", { latency: "14ms", efficiency: "99.8%" });
  }, []);

  /* Tasks state */
  const [tasks, setTasks] = useState<Task[]>([]);
  const [taskInput, setTaskInput] = useState("");
  const addTask = () => {
    const t = taskInput.trim();
    if (!t) return;
    setTasks(prev => [...prev, { id: uid(), text: t, done: false }]);
    setTaskInput("");
  };
  const toggleTask = (id: string) =>
    setTasks(prev => prev.map(t => t.id === id ? { ...t, done: !t.done } : t));
  const deleteTask = (id: string) =>
    setTasks(prev => prev.filter(t => t.id !== id));

  /* Notes state */
  const [notes, setNotes] = useState<Note[]>([]);
  const [noteInput, setNoteInput] = useState("");
  const addNote = () => {
    const n = noteInput.trim();
    if (!n) return;
    setNotes(prev => [...prev, { id: uid(), text: n }]);
    setNoteInput("");
  };
  const deleteNote = (id: string) =>
    setNotes(prev => prev.filter(n => n.id !== id));

  const greeting = getGreeting();

  const getOrbConfig = (): OrbConfig => {
    return { 
      volume: isListening && !isMuted ? volume : 0,
      isChecking 
    };
  };

  return (
    <div className="main-grid h-full w-full relative z-10">
      {/* LEFT COLUMN: SYSTEM HUB */}
      <aside className="flex flex-col gap-3 overflow-y-auto scroll-hide h-full py-2 pr-1">
        
        {/* Gemini Live Vision Feed (Top of Left Column) */}
        <div className="shrink-0 h-[120px] relative overflow-hidden bg-[#06060c] border border-[#00FFFF]/30 clip-cut shadow-[0_0_20px_rgba(0,0,0,0.8)] group">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(0,255,255,0.05)_0%,transparent_100%)]"></div>
          
          {/* Scanline effect */}
          <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.03)_1px,transparent_1px)] bg-[size:100%_4px] pointer-events-none opacity-50"></div>
          
          {/* Edgy corner markers */}
          <div className="absolute top-0 left-0 w-4 h-4 border-t-2 border-l-2 border-[#00FFFF]/50 pointer-events-none z-10"></div>
          <div className="absolute bottom-0 right-0 w-4 h-4 border-b-2 border-r-2 border-[#00FFFF]/50 pointer-events-none z-10"></div>
          <div className="absolute top-0 right-0 w-4 h-4 border-t-2 border-r-2 border-[#00FFFF]/50 pointer-events-none z-10"></div>
          <div className="absolute bottom-0 left-0 w-4 h-4 border-b-2 border-l-2 border-[#00FFFF]/50 pointer-events-none z-10"></div>
          
          {/* Crosshairs */}
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-8 h-8 pointer-events-none z-10 opacity-30">
            <div className="absolute top-0 left-1/2 -translate-x-1/2 w-px h-2 bg-[#00FFFF]"></div>
            <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-px h-2 bg-[#00FFFF]"></div>
            <div className="absolute top-1/2 left-0 -translate-y-1/2 w-2 h-px bg-[#00FFFF]"></div>
            <div className="absolute top-1/2 right-0 -translate-y-1/2 w-2 h-px bg-[#00FFFF]"></div>
          </div>

          <div className="absolute top-2 left-2 flex items-center gap-2 px-2 py-1 bg-black/80 border border-[#00FFFF]/20 z-10 clip-cut-sm shadow-[inset_0_0_10px_rgba(0,255,255,0.1)]">
            <ScanEye size={10} className="text-[#00FFFF]" />
            <span className="text-[8px] font-quantico font-bold text-[#00FFFF] uppercase tracking-[0.2em]">Optics_Link</span>
          </div>
          
          <div className="absolute top-2 right-2 flex items-center gap-1.5 z-10">
             <div className="w-1.5 h-1.5 bg-[#ff3366] rounded-full animate-pulse shadow-[0_0_8px_#ff3366]"></div>
             <span className="text-[8px] font-mono font-bold text-[#ff3366] tracking-[0.2em]">STDBY</span>
          </div>

          <div className="h-full flex flex-col items-center justify-center gap-1.5 opacity-60 relative z-0">
            <div className="flex gap-1.5 mb-1 mt-4">
               <div className="w-1 h-2 bg-[#00FFFF]/50 animate-pulse delay-75"></div>
               <div className="w-1 h-4 bg-[#00FFFF]/80 animate-pulse delay-150"></div>
               <div className="w-1 h-3 bg-[#00FFFF]/50 animate-pulse delay-300"></div>
               <div className="w-1 h-1 bg-[#00FFFF]/30 animate-pulse delay-75"></div>
            </div>
            <span className="text-[10px] font-quantico font-bold text-zinc-300 uppercase tracking-[0.3em] drop-shadow-[0_0_5px_rgba(255,255,255,0.3)]">Gemini Live</span>
            <span className="text-[7px] font-mono text-zinc-500 uppercase tracking-widest">Awaiting Multimodal Stream</span>
          </div>
        </div>

        {/* Dynamic Telemetry */}
        <div className="shrink-0 relative overflow-hidden flex flex-col">
          <div className="absolute -inset-1 bg-gradient-to-b from-[#6137FF]/20 to-transparent blur-md"></div>
          <SystemTelemetry />
        </div>

        {/* Sub-Agents Panel - Moved from center */}
        <div className="flex-1 w-full bg-[#06060c] border border-[#00FFFF]/30 shadow-[0_0_30px_rgba(0,0,0,0.9)] z-10 flex flex-col clip-cut-sm relative">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(0,255,255,0.05)_0%,transparent_100%)]"></div>
          
          <div className="h-8 bg-black flex items-center justify-between px-3 border-b border-[#00FFFF]/20 relative z-10">
            <span className="text-[9px] font-quantico font-bold text-[#00FFFF] uppercase tracking-[0.2em]">Sub_Agents</span>
            <div className="flex items-center gap-2">
              <span className="text-[8px] font-mono text-white bg-[#00FFFF]/20 px-1.5 py-0.5 border border-[#00FFFF]/30 clip-cut-sm">3 ACTIVE</span>
            </div>
          </div>
          <div className="p-3 flex flex-col gap-2 overflow-y-auto scroll-hide relative z-10">
            <div className="flex items-center justify-between bg-black/60 border border-white/5 p-2 clip-cut-sm group hover:border-[#00FFFF]/30 transition-colors">
              <div className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 bg-[#00FFFF] shadow-[0_0_8px_#00FFFF] animate-pulse"></div>
                <span className="text-[9px] font-mono text-zinc-300">parent_delegate_task</span>
              </div>
              <span className="text-[8px] font-mono text-zinc-500 group-hover:text-[#00FFFF]">0.0s</span>
            </div>
            <div className="flex items-center justify-between bg-black/60 border border-white/5 p-2 clip-cut-sm group hover:border-[#6137FF]/30 transition-colors">
              <div className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 bg-[#6137FF] shadow-[0_0_8px_#6137FF] animate-pulse"></div>
                <span className="text-[9px] font-mono text-zinc-300">web_search</span>
              </div>
              <span className="text-[8px] font-mono text-zinc-500 group-hover:text-[#6137FF]">0.8s</span>
            </div>
            <div className="flex items-center justify-between bg-black/60 border border-white/5 p-2 clip-cut-sm group hover:border-white/20 transition-colors">
              <div className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 bg-zinc-500"></div>
                <span className="text-[9px] font-mono text-zinc-500">query_memory</span>
              </div>
              <span className="text-[8px] font-mono text-zinc-600">0.2s</span>
            </div>
          </div>
        </div>
      </aside>

      {/* CENTER COLUMN */}
      <main className="flex flex-col gap-4 overflow-hidden h-full py-2">
        <div className="grid grid-cols-12 gap-4 h-[300px] shrink-0">
          
          {/* Main Orb Container */}
          <div className="col-span-5 relative overflow-hidden group flex items-center justify-center bg-[#06060c] border border-[#6137FF]/30 shadow-[0_0_30px_rgba(97,55,255,0.15)] clip-cut z-10">
            {/* Solo Leveling Shadow Monarch Theming */}
            <div className="absolute inset-0 z-0 pointer-events-none opacity-[0.85] mix-blend-screen overflow-hidden">
              <img src="/assets/monarch/character/jinwoo_idle.png" alt="Ashborn" className="absolute bottom-[-10%] left-1/2 -translate-x-1/2 w-[110%] object-contain object-bottom drop-shadow-[0_0_20px_#6137FF]" />
            </div>
            
            {/* Shadow Particles */}
            <div className="absolute inset-0 z-0 pointer-events-none opacity-40 mix-blend-screen overflow-hidden">
              <img src="/assets/monarch/effects/shadow_particles.png" alt="Particles" className="w-full h-full object-cover animate-pulse" />
            </div>

            {/* Contextual Shadow Monarch Integration Overlay */}
            {(isListening || isSending || isChecking) && (
              <div className="absolute inset-0 z-0 pointer-events-none opacity-40 mix-blend-screen transition-opacity duration-1000">
                <div className="absolute top-1/3 left-1/4 w-32 h-10 bg-[radial-gradient(ellipse_at_center,rgba(0,255,255,0.8)_0%,transparent_70%)] blur-xl"></div>
                <div className="absolute top-1/3 right-1/4 w-32 h-10 bg-[radial-gradient(ellipse_at_center,rgba(0,255,255,0.8)_0%,transparent_70%)] blur-xl"></div>
                {/* Silhouette hint during high processing */}
                {(isSending || isChecking) && (
                  <div className="absolute inset-x-0 bottom-0 h-1/2 bg-gradient-to-t from-[#6137FF]/20 to-transparent"></div>
                )}
              </div>
            )}
            
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(97,55,255,0.1)_0%,transparent_100%)] z-5"></div>
            
            <div className="w-full h-full scale-125 relative z-10 mix-blend-screen">
              <ThreeOrb config={getOrbConfig()} />
            </div>
            
            <div className="absolute top-4 left-4 z-20 flex flex-col gap-1">
              <span className="text-[10px] font-quantico font-bold text-[#00FFFF] uppercase tracking-[0.4em] drop-shadow-[0_0_5px_#00FFFF]">Nexus_Core.v2</span>
              <div className="flex items-center gap-2 bg-black/60 px-2 py-1 border border-white/10 clip-cut-sm">
                <div className={`w-1.5 h-1.5 ${isListening ? 'bg-[#ff3366] animate-pulse shadow-[0_0_8px_#ff3366]' : 'bg-[#6137FF] shadow-[0_0_8px_#6137FF]'}`}></div>
                <span className="text-[8px] font-bold text-white uppercase tracking-[0.2em]">{isChecking ? 'Checking System' : isListening ? 'Active Link' : 'Standby'}</span>
              </div>
            </div>

            <div className="absolute bottom-6 left-1/2 -translate-x-1/2 flex items-center gap-4 z-20 p-2 bg-[#06060c]/80 backdrop-blur-md border border-[#6137FF]/40 clip-cut-sm shadow-[0_0_20px_rgba(0,0,0,0.8)] min-w-[180px] justify-center group-hover:border-[#00FFFF]/50 transition-colors">
              <button
                onClick={toggleMute}
                className={`w-10 h-10 flex items-center justify-center transition-all active:scale-95 clip-cut-sm ${isMuted ? 'bg-[#ff3366]/20 text-[#ff3366] border border-[#ff3366]/50' : 'bg-black/50 text-zinc-400 hover:text-white border border-white/10 hover:border-[#6137FF]/50'}`}
              >
                {isMuted ? <VolumeX size={16} /> : <Volume2 size={16} />}
              </button>
              <button
                onClick={toggleListening}
                className={`w-12 h-12 flex items-center justify-center transition-all shadow-xl active:scale-95 clip-cut ${
                  isListening
                    ? 'bg-[#ff3366] text-white shadow-[0_0_20px_rgba(255,51,102,0.4)]'
                    : 'bg-[#6137FF] text-white shadow-[0_0_20px_rgba(97,55,255,0.4)] hover:bg-[#7b5cff]'
                }`}
              >
                {isListening ? <div className="w-4 h-4 bg-white shadow-[0_0_10px_white]" /> : <Play size={20} className="fill-current translate-x-0.5" />}
              </button>
              <button className="w-10 h-10 bg-black/50 hover:bg-[#00FFFF]/10 text-[#00FFFF] border border-white/10 hover:border-[#00FFFF]/50 flex items-center justify-center transition-all active:scale-95 clip-cut-sm">
                <RefreshCw size={16} className={isSending ? 'animate-spin' : ''} />
              </button>
            </div>
          </div>

          {/* Thinking Area */}
          <div className="col-span-7 p-6 flex flex-col justify-center relative overflow-hidden bg-[#06060c] border border-white/5 hover:border-[#6137FF]/30 transition-colors shadow-lg clip-cut z-0">
            {/* Deep shadow accent */}
            <div className="absolute bottom-0 right-0 w-64 h-64 bg-[radial-gradient(circle_at_bottom_right,rgba(97,55,255,0.1)_0%,transparent_70%)] pointer-events-none"></div>
            
            <div className="flex items-center gap-6 mb-6 relative z-10">
              <div className="w-16 h-16 bg-black border border-[#6137FF]/40 flex items-center justify-center relative clip-cut shadow-[inset_0_0_20px_rgba(97,55,255,0.2)]">
                <Brain size={24} className="text-[#00FFFF]" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-3 mb-2">
                  <h3 className="text-xl font-quantico font-bold tracking-[0.2em] text-white uppercase drop-shadow-md">AI Assistant</h3>
                </div>
                <NexusStatus state={voiceState} />
              </div>
            </div>

            <div className="space-y-6 relative z-10">
              <div className="flex items-start gap-4 p-4 bg-black/40 border border-white/5 clip-cut-sm">
                <div className="mt-1.5 w-2 h-2 bg-[#00FFFF] shadow-[0_0_10px_#00FFFF] shrink-0 transform rotate-45"></div>
                <p className="text-[14px] font-sans text-zinc-300 font-medium tracking-wide leading-relaxed">"{greeting}, Aniket. Initializing neural link for optimal assistance."</p>
              </div>
              
              <div className="space-y-4">
                <div className="space-y-2">
                  <div className="flex justify-between text-[9px] font-quantico font-bold text-[#6137FF] uppercase tracking-[0.3em]">
                    <span>Neural Processing</span>
                    <span className="text-[#00FFFF]">{isListening ? '98.5%' : '14.2%'}</span>
                  </div>
                  <div className="h-1 w-full bg-black border border-white/10 overflow-hidden relative">
                    <div className={`absolute top-0 left-0 h-full bg-[#00FFFF] shadow-[0_0_10px_#00FFFF] transition-all duration-700 ${isListening ? 'w-full' : 'w-[14%]'}`}></div>
                  </div>
                </div>
                <div className="h-1 w-[65%] bg-black border border-white/10 overflow-hidden relative">
                  <div className={`absolute top-0 left-0 h-full bg-[#6137FF] shadow-[0_0_10px_#6137FF] transition-all duration-1000 delay-100 ${isListening ? 'w-[90%]' : 'w-[8%]'}`}></div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Autonomous Shell */}
        <div className="flex-1 flex flex-col overflow-hidden relative bg-[#06060c] border border-white/10 shadow-2xl clip-cut">
          <div className="p-3 border-b border-white/10 flex items-center justify-between bg-black/80">
            <div className="flex items-center gap-4">
              <span className="text-[10px] font-quantico font-bold uppercase tracking-[0.3em] text-zinc-400">Autonomous Shell</span>
              <div className="flex gap-2">
                <div className="px-3 py-1 bg-black text-[#00FFFF] text-[9px] font-bold border border-[#00FFFF]/30 uppercase tracking-widest clip-cut-sm shadow-[inset_0_0_10px_rgba(0,255,255,0.1)]">Instance_042</div>
                <div className="px-3 py-1 bg-black text-[#6137FF] text-[9px] font-bold border border-[#6137FF]/30 uppercase tracking-widest clip-cut-sm shadow-[inset_0_0_10px_rgba(97,55,255,0.1)]">Active</div>
              </div>
            </div>
            <div className="flex gap-4">
              <RefreshCw size={14} className="text-[#6137FF] hover:text-[#00FFFF] cursor-pointer transition-colors" />
              <ExternalLink size={14} className="text-zinc-600 hover:text-white cursor-pointer transition-colors" />
            </div>
          </div>

          <div className="flex-1 flex flex-col overflow-hidden bg-[#06060c]/95 relative">
            {/* Subtle grid background for terminal */}
            <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.02)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.02)_1px,transparent_1px)] bg-[size:20px_20px] pointer-events-none"></div>
            <SystemLogs variant="shell" />
          </div>

        </div>
      </main>

      {/* RIGHT COLUMN: INTERACTION CENTER */}
      <aside className="flex flex-col min-h-0 bg-[#06060c] border border-[#6137FF]/20 shadow-[0_0_20px_rgba(0,0,0,0.8)] clip-cut z-0 py-2 h-full" style={{ overflow: 'visible' }}>
        {/* TRANSCRIPT HEADER */}
        <div className="px-4 pt-4 pb-3 shrink-0 flex items-center justify-between border-b border-white/5 bg-[#06060c]">
          <div className="flex items-center gap-2">
            <MessageSquarePlus size={14} className="text-zinc-500" />
            <span className="text-[12px] font-quantico font-bold uppercase tracking-[0.2em] text-white">
              {uiMode === 'chat' ? 'CHAT MODE' : 'TRANSCRIPT'}
            </span>
          </div>
          <div className="flex items-center gap-3">
            {uiMode === 'voice' && (
              <button
                onClick={toggleListening}
                className={`transition-all p-1.5 clip-cut-sm border ${
                  isChecking
                    ? "text-zinc-400 bg-zinc-500/10 border-zinc-500/30"
                    : isListening 
                    ? "text-[#ff3366] bg-[#ff3366]/10 border-[#ff3366]/50 shadow-[0_0_10px_rgba(255,51,102,0.3)]" 
                    : "text-[#00FFFF] bg-[#00FFFF]/10 border-[#00FFFF]/30 hover:border-[#00FFFF]/60 shadow-[0_0_10px_rgba(0,255,255,0.1)]"
                }`}
                title={isListening ? "Stop listening" : "Start Voice Command"}
              >
                {isListening ? <Mic size={14} className="animate-pulse" /> : <MicOff size={14} />}
              </button>
            )}
            <span className="text-[9px] font-mono font-bold text-[#10b981] uppercase tracking-widest px-2 py-0.5 bg-[#10b981]/10 border border-[#10b981]/30 clip-cut-sm shadow-[0_0_10px_rgba(16,185,129,0.1)]">LIVE-LOG</span>
          </div>
        </div>

        {/* Content area */}
        <div className="flex-1 flex flex-col min-h-0 p-4 overflow-hidden relative">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(97,55,255,0.03)_0%,transparent_70%)] pointer-events-none"></div>

          {/* ── TRANSCRIPT ONLY ── */}
          <div className="flex-1 flex flex-col min-h-0 relative z-10">
            {/* History / Toggle chat icons */}
            <div className="flex justify-end gap-4 mb-3 shrink-0">
              <button className="text-zinc-600 hover:text-[#00FFFF] transition-colors" title="History">
                <History size={16} />
              </button>
              <button 
                className={`transition-colors ${uiMode === 'chat' ? 'text-[#00FFFF]' : 'text-zinc-600 hover:text-[#00FFFF]'}`}
                title={uiMode === 'chat' ? "Hide Chat Input" : "Open Chat Input"}
                onClick={() => setUiMode(uiMode === 'chat' ? 'voice' : 'chat')}
              >
                {uiMode === 'chat' ? <ArrowDown size={16} /> : <ArrowUp size={16} />}
              </button>
            </div>
            <MessageList />
          </div>
        </div>

        {/* Bottom: input area */}
        {uiMode === 'chat' && (
          <div className="px-4 py-3 shrink-0 relative z-20 animate-in fade-in slide-in-from-bottom-2 duration-300" style={{ overflow: 'visible' }}>
            <InputArea />
          </div>
        )}
      </aside>
    </div>
  );
}
