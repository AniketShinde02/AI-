"use client";

import { useEffect, useState, useRef } from 'react';
import { logStore, NexusLog } from '@/lib/logStore';
import { Terminal, Trash2, ShieldCheck, Zap, Brain, AlertCircle } from 'lucide-react';

interface SystemLogsProps {
  variant?: 'shell' | 'minimal';
  maxHeight?: string;
}

export function SystemLogs({ variant = 'minimal', maxHeight = '100%' }: SystemLogsProps) {
  const [logs, setLogs] = useState<NexusLog[]>([]);
  const [expandedLogs, setExpandedLogs] = useState<Set<string>>(new Set());
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setLogs(logStore.getLogs());
    return logStore.subscribe((newLogs) => {
      setLogs([...newLogs]);
    });
  }, []);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs]);

  const toggleExpand = (id: string) => {
    const newSet = new Set(expandedLogs);
    if (newSet.has(id)) newSet.delete(id);
    else newSet.add(id);
    setExpandedLogs(newSet);
  };

  const getLevelColor = (level: NexusLog['level']) => {
    switch (level) {
      case 'info': return 'text-indigo-400';
      case 'warn': return 'text-amber-400';
      case 'error': return 'text-rose-400';
      case 'ai': return 'text-purple-400';
      case 'debug': return 'text-zinc-500';
      default: return 'text-zinc-400';
    }
  };

  const getLevelIcon = (level: NexusLog['level']) => {
    switch (level) {
      case 'info': return <Zap size={10} className="text-indigo-500/70" />;
      case 'warn': return <AlertCircle size={10} className="text-amber-500/70" />;
      case 'error': return <ShieldCheck size={10} className="text-rose-500/70" />;
      case 'ai': return <Brain size={10} className="text-purple-500/70" />;
      case 'debug': return <Terminal size={10} className="text-zinc-600" />;
      default: return null;
    }
  };

  const getLevelBg = (level: NexusLog['level']) => {
    switch (level) {
      case 'info': return 'bg-blue-400/10';
      case 'warn': return 'bg-amber-400/10';
      case 'error': return 'bg-red-400/10';
      case 'ai': return 'bg-purple-400/10';
      case 'debug': return 'bg-zinc-500/10';
      default: return 'bg-zinc-400/10';
    }
  };

  // Shared terminal wrapper style
  const terminalBase = "flex-1 overflow-y-auto scroll-hide font-mono text-[11px] leading-relaxed select-text";

  if (variant === 'shell') {
    return (
      <div 
        ref={scrollRef}
        className={`${terminalBase} p-4 space-y-1`}
        style={{ maxHeight }}
      >
        {logs.length === 0 && (
          <div className="flex gap-2 opacity-40">
            <span className="text-[#6137FF] drop-shadow-[0_0_5px_#6137FF]">nexus@shadow:~$</span>
            <span className="text-zinc-500">standing by...</span>
          </div>
        )}
        {logs.map((log) => (
          <div key={log.id} className="flex gap-3 group whitespace-pre-wrap">
            <span className="text-zinc-600 shrink-0 select-none">[{new Date(log.timestamp).toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })}]</span>
            <span className={`${getLevelColor(log.level)} font-bold shrink-0 uppercase w-10`}>{log.level}</span>
            <span className="text-zinc-300">{log.message}</span>
          </div>
        ))}
        <div className="flex gap-2 items-center text-[#6137FF] mt-2">
          <span className="drop-shadow-[0_0_5px_#6137FF]">nexus@shadow:~$</span>
          <div className="w-1.5 h-3 bg-[#00FFFF] animate-pulse shadow-[0_0_8px_#00FFFF]"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full overflow-hidden bg-[#06060c]">
      <div className="flex items-center justify-between px-4 py-2 border-b border-[#00FFFF]/20 bg-black/60 shadow-[0_0_15px_rgba(0,0,0,0.8)] z-10 relative">
        <div className="absolute top-0 left-0 w-full h-[1px] bg-gradient-to-r from-transparent via-[#6137FF]/50 to-transparent"></div>
        <div className="flex items-center gap-3">
          <div className="flex gap-1.5 mr-2">
            <div className="w-2.5 h-2.5 bg-[#ff3366] transform rotate-45 shadow-[0_0_5px_#ff3366]" />
            <div className="w-2.5 h-2.5 bg-[#00FFFF] transform rotate-45 shadow-[0_0_5px_#00FFFF]" />
            <div className="w-2.5 h-2.5 bg-[#6137FF] transform rotate-45 shadow-[0_0_5px_#6137FF]" />
          </div>
          <span className="text-[10px] font-quantico font-bold uppercase tracking-[0.3em] text-[#00FFFF]">Console_Shadow_v2.0</span>
        </div>
        <button 
          onClick={() => logStore.clear()}
          className="p-1.5 hover:bg-[#ff3366]/20 bg-black border border-white/5 rounded text-zinc-500 hover:text-[#ff3366] hover:border-[#ff3366]/50 transition-all clip-cut-sm"
        >
          <Trash2 size={12} />
        </button>
      </div>
      
      <div 
        ref={scrollRef}
        className={`${terminalBase} p-2 relative z-0`}
      >
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(97,55,255,0.03)_0%,transparent_100%)] pointer-events-none"></div>

        {logs.length === 0 && (
          <div className="h-full flex flex-col items-center justify-center opacity-30 gap-3 font-sans">
            <Terminal size={32} className="text-[#6137FF]" />
            <span className="text-[10px] font-quantico font-bold uppercase tracking-[0.3em] text-zinc-500">No Log Entries</span>
          </div>
        )}
        <div className="divide-y divide-white/[0.05] relative z-10">
          {logs.map((log) => (
            <div 
              key={log.id} 
              className={`py-2 px-3 hover:bg-[#6137FF]/10 transition-all cursor-pointer group border-l-2 clip-cut-sm mb-1 ${expandedLogs.has(log.id) ? 'bg-black/60 border-[#00FFFF] shadow-[inset_0_0_10px_rgba(0,255,255,0.1)]' : 'border-transparent hover:border-[#6137FF]/50'}`}
              onClick={() => toggleExpand(log.id)}
            >
              <div className="flex items-start gap-3">
                <span className="text-[9px] text-[#6137FF] tabular-nums shrink-0 mt-1 opacity-60 group-hover:opacity-100 transition-opacity font-quantico">
                  {new Date(log.timestamp).toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                </span>
                
                <div className="shrink-0 mt-1">
                  {getLevelIcon(log.level)}
                </div>

                <span className={`text-zinc-300 break-words flex-1 tracking-wide font-mono text-[11px] ${log.level === 'ai' ? 'italic text-[#00FFFF]/90' : ''}`}>
                  {log.message}
                  {log.data && !expandedLogs.has(log.id) && (
                    <span className="ml-2 text-[9px] text-[#00FFFF] uppercase tracking-widest font-quantico font-bold opacity-0 group-hover:opacity-100 transition-opacity drop-shadow-[0_0_5px_#00FFFF]">
                      DATA+
                    </span>
                  )}
                </span>
              </div>
              
              {log.data && expandedLogs.has(log.id) && (
                <div className="mt-2 ml-16 p-3 bg-black border border-[#6137FF]/40 overflow-hidden shadow-[inset_0_0_15px_rgba(97,55,255,0.15)] clip-cut-sm">
                  <pre className="text-[10px] text-[#00FFFF]/80 overflow-x-auto whitespace-pre-wrap leading-relaxed scroll-hide font-mono">
                    {JSON.stringify(log.data, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
