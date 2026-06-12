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
    <div className="flex-1 flex flex-col min-h-0 bg-black/20 rounded-2xl border border-white/5 overflow-hidden font-mono p-4">
      {events.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center opacity-30 text-zinc-500 text-xs">
          <span>No active traces</span>
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto scroll-hide pr-2 flex flex-col gap-3 relative">
          {/* Vertical timeline line */}
          <div className="absolute left-4 top-2 bottom-6 w-px bg-white/10 z-0" />
          
          {events.map((evt) => (
            <div 
              key={evt.id} 
              className="flex items-start gap-3 relative z-10 animate-in fade-in slide-in-from-bottom-2 duration-300"
            >
              <div className="w-8 h-8 rounded-full bg-black/80 border border-white/10 shadow-lg flex items-center justify-center shrink-0 text-sm mt-0.5">
                {evt.icon}
              </div>
              <div className="flex flex-col pt-1">
                <span className="text-[12px] font-medium text-zinc-200 tracking-tight leading-snug">
                  {evt.text}
                </span>
                <span className="text-[9px] text-zinc-500 font-bold uppercase tracking-widest mt-0.5">
                  {new Date(evt.timestamp).toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })}
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
