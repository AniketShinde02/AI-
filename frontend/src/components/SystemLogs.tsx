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
            <span className="text-indigo-500">nexus@system:~$</span>
            <span>standing by...</span>
          </div>
        )}
        {logs.map((log) => (
          <div key={log.id} className="flex gap-3 group whitespace-pre-wrap">
            <span className="text-zinc-600 shrink-0 select-none">[{new Date(log.timestamp).toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })}]</span>
            <span className={`${getLevelColor(log.level)} font-bold shrink-0 uppercase w-10`}>{log.level}</span>
            <span className="text-zinc-300">{log.message}</span>
          </div>
        ))}
        <div className="flex gap-2 items-center text-indigo-500 mt-2">
          <span>nexus@system:~$</span>
          <div className="w-1.5 h-3 bg-indigo-500 animate-pulse"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full overflow-hidden bg-black/40">
      <div className="flex items-center justify-between px-3 py-2 border-b border-white/5 bg-white/[0.02]">
        <div className="flex items-center gap-2">
          <div className="flex gap-1.5 mr-2">
            <div className="w-2.5 h-2.5 rounded-full bg-red-500/20 border border-red-500/40" />
            <div className="w-2.5 h-2.5 rounded-full bg-amber-500/20 border border-amber-500/40" />
            <div className="w-2.5 h-2.5 rounded-full bg-emerald-500/20 border border-emerald-500/40" />
          </div>
          <span className="text-[10px] font-bold uppercase tracking-widest text-zinc-500">Console_Nexus_v1.0</span>
        </div>
        <button 
          onClick={() => logStore.clear()}
          className="p-1 hover:bg-white/5 rounded text-zinc-600 hover:text-red-400 transition-colors"
        >
          <Trash2 size={13} />
        </button>
      </div>
      
      <div 
        ref={scrollRef}
        className={`${terminalBase} p-2`}
      >
        {logs.length === 0 && (
          <div className="h-full flex flex-col items-center justify-center opacity-20 gap-2 font-sans">
            <Terminal size={24} />
            <span className="text-[10px] font-bold uppercase tracking-widest">No Log Entries</span>
          </div>
        )}
        <div className="divide-y divide-white/[0.02]">
          {logs.map((log) => (
            <div 
              key={log.id} 
              className={`py-1 px-2 hover:bg-white/[0.02] transition-all cursor-pointer group border-l-2 ${expandedLogs.has(log.id) ? 'bg-white/[0.03] border-indigo-500/40' : 'border-transparent'}`}
              onClick={() => toggleExpand(log.id)}
            >
              <div className="flex items-start gap-2.5">
                <span className="text-[9px] text-zinc-600 tabular-nums shrink-0 mt-1 opacity-50 group-hover:opacity-100 transition-opacity">
                  {new Date(log.timestamp).toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                </span>
                
                <div className="shrink-0 mt-1">
                  {getLevelIcon(log.level)}
                </div>

                <span className={`text-zinc-300 break-words flex-1 tracking-tight ${log.level === 'ai' ? 'italic text-purple-200/90' : ''}`}>
                  {log.message}
                  {log.data && !expandedLogs.has(log.id) && (
                    <span className="ml-2 text-[9px] text-indigo-400/50 uppercase tracking-tighter font-bold opacity-0 group-hover:opacity-100 transition-opacity">
                      DATA+
                    </span>
                  )}
                </span>
              </div>
              
              {log.data && expandedLogs.has(log.id) && (
                <div className="mt-2 ml-16 p-2.5 rounded bg-black/80 border border-white/5 overflow-hidden shadow-2xl">
                  <pre className="text-[10px] text-zinc-400 overflow-x-auto whitespace-pre-wrap leading-relaxed scroll-hide font-mono">
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
