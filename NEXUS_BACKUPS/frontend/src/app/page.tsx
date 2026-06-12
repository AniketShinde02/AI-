"use client";

import { useState, useRef, KeyboardEvent } from "react";
import dynamic from "next/dynamic";
import { InputArea } from "@/components/InputArea";
import { useNexus } from "@/contexts/NexusContext";
import { MessageList } from "@/components/MessageList";
import { SystemLogs } from "@/components/SystemLogs";
import {
  ScanEye, Mic, Cpu, Globe, Command,
  Power, Play, VolumeX, Volume2,
  RefreshCw, ExternalLink, Brain, User, Send,
  History, MessageSquarePlus,
  Plus, Check, Trash2, StickyNote, CheckSquare, ArrowUp,
  Terminal,
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
    uiMode, setUiMode, 
    isListening, isMuted, volume, 
    toggleListening, toggleMute, 
    isSending, isChecking,
    persona, setPersona,
    perplexityMode, setPerplexityMode,
    voiceState
  } = useNexus();
  const [activeTab, setActiveTab] = useState<'chat' | 'logs' | 'tasks' | 'notes'>('chat');

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
    <div className="main-container max-w-[1800px] mx-auto">
      {/* LEFT COLUMN: SYSTEM HUB */}
      <aside className="flex flex-col gap-3 overflow-hidden">
        {/* Dynamic Telemetry */}
        <SystemTelemetry />

        {/* Vision Core (Live Feed) */}
        <div className="glass flex-1 relative overflow-hidden bg-black/40 group">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(99,102,241,0.03)_0%,transparent_100%)]"></div>
          <div className="absolute top-4 left-4 flex items-center gap-2 px-2.5 py-1.5 bg-black/60 border border-white/5 rounded-lg z-10">
            <div className="w-1.5 h-1.5 bg-red-500 rounded-full animate-pulse"></div>
            <span className="text-[9px] font-bold text-white uppercase tracking-wider">Vision_01</span>
          </div>
          <div className="h-full flex flex-col items-center justify-center gap-4 opacity-40 group-hover:opacity-60 transition-opacity">
            <ScanEye className="text-zinc-600" size={40} />
            <span className="text-[9px] font-bold text-zinc-500 uppercase tracking-[0.3em]">Establishing Link</span>
          </div>
        </div>



        {/* Fast Actions */}
        <div className="glass p-3 grid grid-cols-2 gap-2">
          <button
            onClick={toggleListening}
            className={`flex flex-col items-center gap-1.5 p-3 rounded-xl transition-all group ${isListening ? 'bg-indigo-500/10' : 'hover:bg-white/5'}`}
          >
            <Mic size={14} className={isListening ? 'text-indigo-400' : 'text-zinc-500 group-hover:text-indigo-400 transition-colors'} />
            <span className={`text-[8px] font-bold uppercase tracking-widest ${isListening ? 'text-indigo-400' : 'text-zinc-600'}`}>Voice</span>
          </button>
          <button className="flex flex-col items-center gap-1.5 p-3 rounded-xl hover:bg-white/5 transition-all group">
            <Cpu size={14} className="text-zinc-500 group-hover:text-indigo-400 transition-colors" />
            <span className="text-[8px] font-bold uppercase tracking-widest text-zinc-600">Agents</span>
          </button>
          <button className="flex flex-col items-center gap-1.5 p-3 rounded-xl hover:bg-white/5 transition-all group">
            <Globe size={14} className="text-zinc-500 group-hover:text-indigo-400 transition-colors" />
            <span className="text-[8px] font-bold uppercase tracking-widest text-zinc-600">Network</span>
          </button>
          <button className="flex flex-col items-center gap-1.5 p-3 rounded-xl hover:bg-white/5 transition-all group">
            <Command size={14} className="text-zinc-500 group-hover:text-indigo-400 transition-colors" />
            <span className="text-[8px] font-bold uppercase tracking-widest text-zinc-600">Shell</span>
          </button>
        </div>
      </aside>

      {/* CENTER COLUMN */}
      <main className="flex flex-col gap-3 overflow-hidden h-full">
        <div className="grid grid-cols-12 gap-3 h-[280px] shrink-0">
          {/* Main Orb Container */}
          <div className="glass col-span-5 relative overflow-hidden group flex items-center justify-center">
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(99,102,241,0.05)_0%,transparent_100%)]"></div>
            <div className="w-full h-full scale-125">
              <ThreeOrb config={getOrbConfig()} />
            </div>
            <div className="absolute top-4 left-4 z-10 flex flex-col gap-0.5">
              <span className="text-[10px] font-black text-white/90 uppercase tracking-[0.3em]">Nexus_Core.v1</span>
              <div className="flex items-center gap-1.5">
                <div className={`w-1.5 h-1.5 rounded-full ${isListening ? 'bg-red-500 animate-pulse' : 'bg-indigo-400'}`}></div>
                <span className="text-[8px] font-bold text-zinc-500 uppercase tracking-widest">{isChecking ? 'Checking System' : isListening ? 'Active Link' : 'Standby'}</span>
              </div>
            </div>

            <div className="absolute bottom-6 left-1/2 -translate-x-1/2 flex items-center gap-4 z-10 p-2 bg-black/40 backdrop-blur-xl border border-white/5 rounded-full shadow-2xl min-w-[160px] justify-center">
              <button
                onClick={toggleMute}
                className={`w-10 h-10 rounded-full flex items-center justify-center transition-all active:scale-95 ${isMuted ? 'bg-red-500/20 text-red-400' : 'bg-white/5 text-zinc-400 hover:bg-white/10'}`}
              >
                {isMuted ? <VolumeX size={16} /> : <Volume2 size={16} />}
              </button>
              <button
                onClick={toggleListening}
                className={`w-12 h-12 rounded-full flex items-center justify-center transition-all shadow-xl active:scale-95 ${
                  isListening
                    ? 'bg-red-500 text-white shadow-red-500/20 hover:bg-red-600'
                    : 'bg-indigo-600 text-white shadow-indigo-500/20 hover:scale-105'
                }`}
              >
                {isListening ? <div className="w-4 h-4 bg-white rounded-sm" /> : <Play size={20} className="fill-current translate-x-0.5" />}
              </button>
              <button className="w-10 h-10 bg-white/5 hover:bg-white/10 text-indigo-400 rounded-full flex items-center justify-center transition-all active:scale-95">
                <RefreshCw size={16} className={isSending ? 'animate-spin' : ''} />
              </button>
            </div>
          </div>

          {/* Thinking Area */}
          <div className="glass col-span-7 p-6 flex flex-col justify-center relative overflow-hidden shrink-0">
            <div className="flex items-center gap-6 mb-6">
              <div className="w-16 h-16 rounded-2xl bg-indigo-500/5 border border-indigo-500/10 flex items-center justify-center relative">
                <Brain size={24} className="text-indigo-400" />
                <div className="absolute inset-0 bg-indigo-500/10 blur-xl rounded-full opacity-50"></div>
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <h3 className="text-xl font-black tracking-tight text-white/90 uppercase">AI Assistant</h3>
                </div>
                <NexusStatus state={voiceState} />
              </div>
            </div>

            <div className="space-y-5">
              <div className="flex items-start gap-4">
                <div className="mt-1.5 w-1.5 h-1.5 rounded-full bg-indigo-500 shadow-[0_0_8px_rgba(99,102,241,0.8)] shrink-0"></div>
                <p className="text-lg text-zinc-300 font-medium tracking-tight leading-snug">"{greeting}, Aniket. Initializing neural link for optimal assistance."</p>
              </div>
              <div className="space-y-3">
                <div className="space-y-1.5">
                  <div className="flex justify-between text-[8px] font-black text-zinc-600 uppercase tracking-widest">
                    <span>Processing Power</span>
                    <span>{isListening ? '98%' : '14%'}</span>
                  </div>
                  <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden">
                    <div className={`h-full bg-gradient-to-r from-indigo-500 to-purple-500 rounded-full transition-all duration-700 ${isListening ? 'w-full' : 'w-[14%]'}`}></div>
                  </div>
                </div>
                <div className="h-1.5 w-[65%] bg-white/5 rounded-full overflow-hidden">
                  <div className={`h-full bg-gradient-to-r from-purple-500 to-pink-500 rounded-full transition-all duration-1000 delay-100 ${isListening ? 'w-[90%]' : 'w-[8%]'}`}></div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Autonomous Shell */}
        <div className="glass flex-1 flex flex-col overflow-hidden relative">
          <div className="p-4 border-b border-white/5 flex items-center justify-between bg-white/[0.01]">
            <div className="flex items-center gap-4">
              <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-zinc-500">Autonomous Shell</span>
              <div className="flex gap-2">
                <div className="px-2 py-0.5 bg-indigo-500/10 text-indigo-400 text-[9px] font-bold rounded border border-indigo-500/20 uppercase tracking-tighter">Instance_042</div>
                <div className="px-2 py-0.5 bg-emerald-500/10 text-emerald-400 text-[9px] font-bold rounded border border-emerald-500/20 uppercase tracking-tighter">Working</div>
              </div>
            </div>
            <div className="flex gap-4">
              <RefreshCw size={12} className="text-zinc-600 hover:text-zinc-400 cursor-pointer transition-colors" />
              <ExternalLink size={12} className="text-zinc-600 hover:text-zinc-400 cursor-pointer transition-colors" />
            </div>
          </div>

          <div className="flex-1 flex flex-col overflow-hidden bg-black/60">
            <SystemLogs variant="shell" />
          </div>

          {/* Floating Browser Preview */}
          <div className="absolute bottom-8 right-8 w-64 h-40 glass border-indigo-500/30 overflow-hidden shadow-2xl shadow-black/50 hover:scale-105 transition-transform z-10 hidden md:block">
            <div className="h-6 bg-white/5 w-full flex items-center px-3 border-b border-white/5">
              <div className="flex gap-1.5">
                <div className="w-1.5 h-1.5 rounded-full bg-zinc-700"></div>
                <div className="w-1.5 h-1.5 rounded-full bg-zinc-700"></div>
                <div className="w-1.5 h-1.5 rounded-full bg-zinc-700"></div>
              </div>
              <div className="flex-1 mx-4 h-3 bg-black/40 rounded-md border border-white/5"></div>
            </div>
            <div className="p-4 space-y-3">
              <div className="flex gap-3">
                <div className="w-10 h-10 rounded-lg bg-white/5 shimmer"></div>
                <div className="flex-1 space-y-2">
                  <div className="h-2 bg-white/5 rounded w-full"></div>
                  <div className="h-2 bg-white/5 rounded w-2/3"></div>
                </div>
              </div>
              <div className="h-10 bg-indigo-500/10 border border-indigo-500/10 rounded-lg w-full flex items-center justify-center">
                <span className="text-[8px] font-bold text-indigo-400 uppercase tracking-widest">Tool: browser_subagent</span>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* RIGHT COLUMN: INTERACTION CENTER */}
      {/* overflow-visible so the model dropdown can escape the aside boundary */}
      <aside className="glass flex flex-col min-h-0" style={{ overflow: 'visible' }}>
        {/* Tab header */}
        <div className="px-3 pt-2 pb-1.5 shrink-0">
          <div className="flex items-center justify-end gap-1.5 mb-1.5">
            <div className="w-1.5 h-1.5 rounded-full bg-indigo-500 shadow-[0_0_5px_rgba(99,102,241,0.5)]"></div>
            <div className="w-1.5 h-1.5 rounded-full bg-white/10"></div>
          </div>
          <div className="flex p-1 bg-black/40 rounded-xl border border-white/5 shadow-inner">
            {(['chat', 'logs', 'tasks', 'notes'] as const).map(tab => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`flex-1 py-2 text-[9px] font-black uppercase tracking-[0.2em] rounded-lg transition-all ${activeTab === tab ? 'tab-active' : 'text-zinc-500 hover:text-zinc-300'}`}
              >
                {tab}
              </button>
            ))}
          </div>
          {/* Accent line under active tab indicator */}
          <div className="mt-1.5 h-px bg-gradient-to-r from-transparent via-indigo-500/30 to-transparent" />
        </div>

        {/* Content area — scrollable, clipped, but input wrapper below stays overflow-visible */}
        <div className="flex-1 flex flex-col min-h-0 p-3 overflow-hidden">

          {/* ── CHAT ── */}
          {activeTab === 'chat' && (
            <div className="flex-1 flex flex-col min-h-0">
              {/* History / New chat icons */}
              <div className="flex justify-end gap-3 mb-2 shrink-0">
                <button className="text-zinc-600 hover:text-indigo-400 transition-colors" title="History">
                  <History size={14} />
                </button>
                <button className="text-zinc-600 hover:text-indigo-400 transition-colors" title="New Chat">
                  <MessageSquarePlus size={14} />
                </button>
              </div>
              <MessageList />
            </div>
          )}

          {/* ── LOGS ── */}
          {activeTab === 'logs' && (
            <div className="flex-1 flex flex-col min-h-0 bg-black/20 rounded-2xl border border-white/5 overflow-hidden">
              <SystemLogs variant="minimal" />
            </div>
          )}

          {/* ── TASKS ── */}
          {activeTab === 'tasks' && (
            <div className="flex flex-col gap-3 h-full">
              {tasks.length === 0 && (
                <div className="flex-1 flex flex-col items-center justify-center gap-2 opacity-30">
                  <CheckSquare size={28} className="text-indigo-400" />
                  <span className="text-[10px] font-bold uppercase tracking-widest text-zinc-500">No active tasks</span>
                </div>
              )}
              {tasks.length > 0 && (
                <div className="flex-1 space-y-1.5 overflow-y-auto scroll-hide">
                  {tasks.map(task => (
                    <div
                      key={task.id}
                      className={`flex items-center gap-2.5 px-3 py-2.5 rounded-xl border transition-all group ${
                        task.done
                          ? 'border-white/[0.04] bg-white/[0.01] opacity-50'
                          : 'border-white/[0.08] bg-white/[0.03] hover:border-indigo-500/20'
                      }`}
                    >
                      <button
                        onClick={() => toggleTask(task.id)}
                        className={`w-4 h-4 rounded-full border flex items-center justify-center shrink-0 transition-all ${
                          task.done ? 'bg-indigo-500 border-indigo-500' : 'border-white/20 hover:border-indigo-400'
                        }`}
                      >
                        {task.done && <Check size={9} className="text-white" />}
                      </button>
                      <span className={`flex-1 text-[11px] font-medium ${task.done ? 'line-through text-zinc-600' : 'text-zinc-300'}`}>
                        {task.text}
                      </span>
                      <button
                        onClick={() => deleteTask(task.id)}
                        className="opacity-0 group-hover:opacity-100 text-zinc-700 hover:text-red-400 transition-all"
                      >
                        <Trash2 size={11} />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* ── NOTES ── */}
          {activeTab === 'notes' && (
            <div className="flex flex-col gap-3 h-full">
              {notes.length === 0 && (
                <div className="flex-1 flex flex-col items-center justify-center gap-2 opacity-30">
                  <StickyNote size={28} className="text-indigo-400" />
                  <span className="text-[10px] font-bold uppercase tracking-widest text-zinc-500">No notes saved</span>
                </div>
              )}
              {notes.length > 0 && (
                <div className="flex-1 space-y-1.5 overflow-y-auto scroll-hide">
                  {notes.map(note => (
                    <div
                      key={note.id}
                      className="flex items-start gap-2.5 px-3 py-2.5 rounded-xl border border-white/[0.08] bg-white/[0.03] hover:border-indigo-500/20 transition-all group"
                    >
                      <StickyNote size={11} className="text-indigo-400/60 mt-0.5 shrink-0" />
                      <span className="flex-1 text-[11px] font-medium text-zinc-300 leading-relaxed">{note.text}</span>
                      <button
                        onClick={() => deleteNote(note.id)}
                        className="opacity-0 group-hover:opacity-100 text-zinc-700 hover:text-red-400 transition-all shrink-0"
                      >
                        <Trash2 size={11} />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Bottom: input area — conditionally swap for task/note add bar */}
        <div className="px-3 py-3 shrink-0" style={{ overflow: 'visible' }}>
          <div className={activeTab === 'chat' ? 'block' : 'hidden'}>
            <InputArea />
          </div>

          <div className={activeTab === 'tasks' ? 'block' : 'hidden'}>
            <div className="flex gap-2 items-center rounded-2xl border border-white/10 bg-black/50 backdrop-blur-xl px-3 py-2.5 focus-within:border-indigo-500/40 transition-colors">
              <Plus size={13} className="text-zinc-600 shrink-0" />
              <input
                type="text"
                value={taskInput}
                onChange={e => setTaskInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && addTask()}
                placeholder="Add a task…"
                className="flex-1 bg-transparent text-[12px] text-white placeholder:text-zinc-600 outline-none"
              />
              <button
                onClick={addTask}
                disabled={!taskInput.trim()}
                className="w-6 h-6 rounded-full bg-indigo-600 hover:bg-indigo-500 disabled:bg-white/10 text-white flex items-center justify-center transition-all active:scale-90 disabled:text-zinc-600"
              >
                <ArrowUp size={11} />
              </button>
            </div>
          </div>

          <div className={activeTab === 'notes' ? 'block' : 'hidden'}>
            <div className="flex gap-2 items-center rounded-2xl border border-white/10 bg-black/50 backdrop-blur-xl px-3 py-2.5 focus-within:border-indigo-500/40 transition-colors">
              <StickyNote size={13} className="text-zinc-600 shrink-0" />
              <input
                type="text"
                value={noteInput}
                onChange={e => setNoteInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && addNote()}
                placeholder="Write a note…"
                className="flex-1 bg-transparent text-[12px] text-white placeholder:text-zinc-600 outline-none"
              />
              <button
                onClick={addNote}
                disabled={!noteInput.trim()}
                className="w-6 h-6 rounded-full bg-indigo-600 hover:bg-indigo-500 disabled:bg-white/10 text-white flex items-center justify-center transition-all active:scale-90 disabled:text-zinc-600"
              >
                <ArrowUp size={11} />
              </button>
            </div>
          </div>
        </div>
      </aside>
    </div>
  );
}
