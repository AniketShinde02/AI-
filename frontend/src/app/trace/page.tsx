"use client";

import { SystemTrace } from "@/components/SystemTrace";
import { Activity, Zap, Clock, Terminal } from "lucide-react";

export default function TracePage() {
  return (
    <div className="h-full flex flex-col overflow-hidden p-4 gap-4">
      {/* Header */}
      <div className="flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-[#00FFFF]/10 border border-[#00FFFF]/30 flex items-center justify-center clip-cut">
            <Activity size={16} className="text-[#00FFFF]" />
          </div>
          <div>
            <h1 className="text-[11px] font-quantico font-bold uppercase tracking-[0.3em] text-white">System Trace</h1>
            <p className="text-[9px] font-mono text-zinc-500 uppercase tracking-widest">Execution Timeline Monitor</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5 px-3 py-1 bg-[#00FFFF]/10 border border-[#00FFFF]/30 clip-cut-sm">
            <div className="w-1.5 h-1.5 bg-[#00FFFF] rounded-full animate-pulse shadow-[0_0_6px_#00FFFF]" />
            <span className="text-[9px] font-bold uppercase tracking-widest text-[#00FFFF]">Live Feed</span>
          </div>
        </div>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-3 gap-3 shrink-0">
        {[
          { label: "Exec Calls", value: "—", icon: Terminal, color: "#6137FF" },
          { label: "Avg Latency", value: "—", icon: Clock, color: "#00FFFF" },
          { label: "Events", value: "—", icon: Zap, color: "#10b981" },
        ].map(({ label, value, icon: Icon, color }) => (
          <div
            key={label}
            className="bg-[#06060c] border border-white/5 clip-cut p-4 flex items-center gap-3"
            style={{ borderColor: `${color}20` }}
          >
            <div className="w-8 h-8 flex items-center justify-center border clip-cut-sm" style={{ background: `${color}15`, borderColor: `${color}30` }}>
              <Icon size={14} style={{ color }} />
            </div>
            <div>
              <p className="text-[9px] font-mono text-zinc-500 uppercase tracking-widest">{label}</p>
              <p className="text-lg font-bold font-quantico" style={{ color }}>{value}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Trace Timeline */}
      <div className="flex-1 bg-[#06060c] border border-white/5 clip-cut overflow-hidden flex flex-col shadow-inner">
        <div className="h-8 bg-black/60 border-b border-white/5 flex items-center px-4 gap-3 shrink-0">
          <div className="w-1.5 h-1.5 bg-[#00FFFF] rounded-full animate-pulse shadow-[0_0_6px_#00FFFF]" />
          <span className="text-[9px] font-quantico font-bold uppercase tracking-widest text-zinc-400">Execution Log</span>
        </div>
        <div className="flex-1 overflow-y-auto scroll-hide p-4">
          <SystemTrace />
        </div>
      </div>
    </div>
  );
}
