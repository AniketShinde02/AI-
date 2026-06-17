"use client";

import React, { useEffect, useState, useRef } from "react";
import { Activity, CheckCircle2, ChevronRight } from "lucide-react";

interface StatusEvent {
  id: string;
  message: string;
  timestamp: number;
}

export function LiveStatusWindow() {
  const [events, setEvents] = useState<StatusEvent[]>([]);
  const containerRef = useRef<HTMLDivElement>(null);

  // Expose a global method to add status events so other components can trigger it
  useEffect(() => {
    const handleAddStatus = (e: CustomEvent<{ message: string }>) => {
      setEvents((prev) => {
        const newEvents = [...prev, { id: Math.random().toString(36).substring(7), message: e.detail.message, timestamp: Date.now() }];
        // Keep only last 50 events
        return newEvents.slice(-50);
      });
    };

    window.addEventListener("nexus_status_event" as any, handleAddStatus);
    return () => window.removeEventListener("nexus_status_event" as any, handleAddStatus);
  }, []);

  // Auto-scroll to bottom
  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [events]);

  return (
    <div className="shrink-0 h-[120px] bg-[#06060c] border border-white/10 shadow-[0_0_30px_rgba(0,0,0,0.9)] z-10 flex flex-col clip-cut-sm relative mt-3">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(0,255,255,0.02)_0%,transparent_100%)] pointer-events-none"></div>
      
      <div className="h-7 bg-black/80 flex items-center px-2 border-b border-white/5 relative z-10">
        <Activity size={10} className="text-[#10b981] mr-1.5 animate-pulse" />
        <span className="text-[9px] font-quantico font-bold text-zinc-300 uppercase tracking-[0.2em]">Live_Status</span>
      </div>
      
      <div ref={containerRef} className="flex-1 p-2 flex flex-col gap-1 overflow-y-auto scroll-hide relative z-10">
        {events.length === 0 ? (
          <div className="h-full flex items-center justify-center text-[9px] font-mono text-zinc-600 uppercase tracking-widest">
            Awaiting Actions
          </div>
        ) : (
          events.map((event) => (
            <div key={event.id} className="flex items-start gap-1.5 animate-in fade-in slide-in-from-left-2 duration-300">
              <CheckCircle2 size={10} className="text-[#10b981] shrink-0 mt-[2px]" />
              <span className="text-[10px] font-mono text-zinc-400 leading-tight">
                {event.message}
              </span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
