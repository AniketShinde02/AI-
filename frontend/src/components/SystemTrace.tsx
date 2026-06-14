import React, { useEffect, useState, useRef } from 'react';
import { traceStore, TraceEvent } from '@/lib/traceStore';

export function SystemTrace() {
  const [events, setEvents] = useState<TraceEvent[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setEvents(traceStore.getEvents());
    const unsubscribe = traceStore.subscribe((newEvents) => {
      setEvents(newEvents);
    });
    return () => unsubscribe();
  }, []);

  useEffect(() => {
    // Auto-scroll to bottom
    if (bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [events]);

  return (
    <div className="flex-1 flex flex-col min-h-0 bg-[#06060c]/80 border border-white/10 overflow-hidden font-mono p-4 clip-cut shadow-[inset_0_0_20px_rgba(0,0,0,0.8)] h-full relative z-10">
      {/* Grid overlay */}
      <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.02)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.02)_1px,transparent_1px)] bg-[size:16px_16px] pointer-events-none z-0"></div>

      {events.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center opacity-40 text-zinc-500 z-10">
          <span className="text-[10px] font-quantico font-bold uppercase tracking-[0.3em]">No Active Traces</span>
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto scroll-hide pr-2 flex flex-col gap-4 relative z-10">
          {/* Vertical timeline line */}
          <div className="absolute left-4 top-2 bottom-6 w-px bg-gradient-to-b from-[#6137FF] via-[#00FFFF]/50 to-transparent z-0" />
          
          {events.map((evt) => (
            <div 
              key={evt.id} 
              className="flex items-start gap-3 relative z-10 animate-in fade-in slide-in-from-bottom-2 duration-300 group"
            >
              <div className="w-8 h-8 bg-black border border-[#6137FF]/50 shadow-[0_0_10px_rgba(97,55,255,0.2)] flex items-center justify-center shrink-0 text-sm mt-0.5 clip-cut-sm group-hover:border-[#00FFFF] group-hover:shadow-[0_0_10px_rgba(0,255,255,0.4)] transition-all">
                {evt.icon}
              </div>
              <div className="flex flex-col pt-1 bg-black/60 px-3 py-1.5 border border-white/5 clip-cut-sm flex-1 group-hover:bg-[#6137FF]/10 transition-colors">
                <span className="text-[11px] font-mono font-medium text-zinc-300 tracking-wide leading-snug">
                  {evt.text}
                </span>
                <span className="text-[9px] text-[#00FFFF]/70 font-quantico font-bold uppercase tracking-[0.2em] mt-1">
                  {new Date(evt.timestamp).toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit', fractionalSecondDigits: 2 })}
                </span>
              </div>
            </div>
          ))}
          <div ref={bottomRef} className="h-2 shrink-0" />
        </div>
      )}
    </div>
  );
}
